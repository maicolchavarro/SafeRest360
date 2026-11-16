"""Offline tests, runnable without installing FastAPI or the vision stack."""
import asyncio
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from app.services.telegram_client import TelegramDeliveryError, send_alert_notification, normalize_chat_id


def complete(value):
    # Execute a coroutine that uses only mocked I/O. No socket/event loop is needed.
    if not asyncio.iscoroutine(value):
        return value
    try:
        value.send(None)
    except StopIteration as done:
        return done.value
    finally:
        value.close()
    raise AssertionError("Unexpected real asynchronous I/O in offline test")

async def inline_thread(function, *args, **kwargs):
    return function(*args, **kwargs)

class TelegramClientTests(unittest.TestCase):

    def setUp(self):
        thread = patch('app.services.telegram_client.asyncio.to_thread', inline_thread)
        thread.start()
        self.addCleanup(thread.stop)

    def send(self, **kwargs):
        return complete(send_alert_notification('-1001234567890', 'no_entry', 'Cocina: persona en zona restringida', 'high', token='123456:TEST_TOKEN', test_mode=False, **kwargs))

    def test_dry_run_does_not_contact_network(self):
        with patch('app.services.telegram_client.urlopen') as opened:
            result = complete(send_alert_notification('123456', 'test', 'Demo', 'low'))
        self.assertEqual(result['status'], 'test')
        self.assertIsNone(result['message_id'])
        opened.assert_not_called()

    def test_payload_and_chat_scoped_message_id(self):
        with patch('app.services.telegram_client.urlopen', return_value=io.BytesIO(b'{"ok":true,"result":{"message_id":42}}')) as opened:
            result = complete(self.send())
        request = opened.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload['chat_id'], '-1001234567890')
        self.assertIn('Cocina', payload['text'])
        self.assertNotIn('parse_mode', payload)
        self.assertEqual(result, {'status': 'sent', 'message_id': '-1001234567890:42'})
        self.assertEqual(opened.call_args.kwargs['timeout'], 10.0)

    def test_missing_token_fails_before_network(self):
        with patch('app.services.telegram_client.urlopen') as opened:
            with self.assertRaises(TelegramDeliveryError):
                complete(send_alert_notification('123', 'test', 'Demo', 'low', test_mode=False))
        opened.assert_not_called()

    def test_invalid_token_fails_before_network(self):
        with patch('app.services.telegram_client.urlopen') as opened:
            with self.assertRaises(TelegramDeliveryError):
                complete(send_alert_notification('123', 'test', 'Demo', 'low', token='../bad', test_mode=False))
        opened.assert_not_called()

    def test_http_errors_are_sanitized(self):
        for code, expected in [(401, 'failed'), (403, 'failed'), (429, 'failed'), (503, 'unknown')]:
            with self.subTest(code=code):
                error = HTTPError('https://api.telegram.org/botSECRET/sendMessage', code, 'SECRET', {}, None)
                with patch('app.services.telegram_client.urlopen', side_effect=error) as opened:
                    with self.assertRaises(TelegramDeliveryError) as ctx:
                        complete(self.send())
                self.assertEqual(ctx.exception.status, expected)
                self.assertNotIn('SECRET', str(ctx.exception))
                self.assertEqual(opened.call_count, 1)

    def test_timeout_and_network_error_are_unknown_and_never_retried(self):
        for error in (TimeoutError('SECRET'), URLError('SECRET')):
            with patch('app.services.telegram_client.urlopen', side_effect=error) as opened:
                with self.assertRaises(TelegramDeliveryError) as ctx:
                    complete(self.send())
            self.assertEqual(ctx.exception.status, 'unknown')
            self.assertNotIn('SECRET', str(ctx.exception))
            self.assertEqual(opened.call_count, 1)

    def test_provider_rejection_not_marked_sent(self):
        with patch('app.services.telegram_client.urlopen', return_value=io.BytesIO(b'{"ok":false}')):
            with self.assertRaises(TelegramDeliveryError) as ctx:
                complete(self.send())
        self.assertEqual(ctx.exception.status, 'failed')

    def test_unrecognized_success_is_unknown(self):
        for body in (b'not-json', b'[]', b'{"ok":true}', b'{"ok":true,"result":{"message_id":true}}'):
            with patch('app.services.telegram_client.urlopen', return_value=io.BytesIO(body)):
                with self.assertRaises(TelegramDeliveryError) as ctx:
                    complete(self.send())
            self.assertEqual(ctx.exception.status, 'unknown')

    def test_long_message_is_bounded(self):
        with patch('app.services.telegram_client.urlopen', return_value=io.BytesIO(b'{"ok":true,"result":{"message_id":1}}')) as opened:
            complete(send_alert_notification('123', 'test', 'x' * 10000, 'low', token='1:T', test_mode=False))
        self.assertLessEqual(len(json.loads(opened.call_args.args[0].data)['text']), 4096)

    def test_invalid_timeout_is_rejected(self):
        with self.assertRaises(TelegramDeliveryError):
            complete(self.send(timeout=0))

    def test_chat_id_validation(self):
        self.assertEqual(normalize_chat_id(' 12345 '), '12345')
        self.assertEqual(normalize_chat_id('-10012345'), '-10012345')
        for value in ('', '0', 'abc', '+573000000', '1/../secret', '1' * 25):
            with self.subTest(value=value):
                with self.assertRaises(TelegramDeliveryError):
                    normalize_chat_id(value)

    def test_photo_multipart_and_caption_limit(self):
        photo = b"\xff\xd8snapshot\xff\xd9"
        with patch("app.services.telegram_client.urlopen", return_value=io.BytesIO(b'{"ok":true,"result":{"message_id":9}}')) as opened:
            result = complete(send_alert_notification("123", "test", "x" * 5000, "high", token="1:T", test_mode=False, photo_bytes=photo))
        request = opened.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/sendPhoto"))
        self.assertIn(photo, request.data)
        self.assertIn(b'name="chat_id"\r\n\r\n123', request.data)
        caption = request.data.split(b'name="caption"\r\n\r\n')[1].split(b"\r\n--")[0].decode()
        self.assertLessEqual(len(caption), 1024)
        self.assertEqual(result["message_id"], "123:9")
        self.assertEqual(opened.call_count, 1)

    def test_photo_timeout_never_sends_a_second_message(self):
        with patch("app.services.telegram_client.urlopen", side_effect=TimeoutError("SECRET")) as opened:
            with self.assertRaises(TelegramDeliveryError) as ctx:
                self.send(photo_bytes=b"image")
        self.assertEqual(ctx.exception.status, "unknown")
        self.assertEqual(opened.call_count, 1)

    def test_rejected_photo_can_fallback_to_text(self):
        error = HTTPError("https://api.telegram.org/botSECRET/sendPhoto", 400, "SECRET", {}, None)
        with patch("app.services.telegram_client.urlopen", side_effect=[error, io.BytesIO(b'{"ok":true,"result":{"message_id":10}}')]) as opened:
            result = self.send(photo_bytes=b"image")
        self.assertEqual(result["status"], "sent")
        self.assertEqual(opened.call_count, 2)
        self.assertTrue(opened.call_args.args[0].full_url.endswith("/sendMessage"))

    def test_photo_rate_limit_and_forbidden_are_not_retried_as_text(self):
        for code in (401, 403, 429, 500):
            with self.subTest(code=code):
                error = HTTPError("https://api.telegram.org/botSECRET/sendPhoto", code, "SECRET", {}, None)
                with patch("app.services.telegram_client.urlopen", side_effect=error) as opened:
                    with self.assertRaises(TelegramDeliveryError) as ctx:
                        self.send(photo_bytes=b"image")
                self.assertEqual(opened.call_count, 1)
                self.assertNotIn("SECRET", str(ctx.exception))

    def test_photo_test_mode_never_contacts_network(self):
        with patch("app.services.telegram_client.urlopen") as opened:
            result = complete(send_alert_notification("123", "test", "Photo demo", "low", photo_bytes=b"image"))
        self.assertEqual(result["status"], "test")
        opened.assert_not_called()

if __name__ == '__main__':
    unittest.main()
