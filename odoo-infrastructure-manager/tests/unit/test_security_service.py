from django.test import TestCase

from apps.core.services.security_service import (
    sanitize_html,
    sanitize_json_body,
    validate_email,
    validate_password_strength,
    validate_string,
)


class SanitizeHtmlTests(TestCase):
    def test_plain_text_passes_through(self):
        self.assertEqual(sanitize_html("  نص عادي  "), "نص عادي")

    def test_script_tag_is_escaped(self):
        self.assertEqual(
            sanitize_html("<script>alert(1)</script>"),
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        )

    def test_onerror_attributes_are_escaped(self):
        self.assertEqual(
            sanitize_html("<img src=x onerror=alert(1)>"),
            "&lt;img src=x onerror=alert(1)&gt;",
        )

    def test_max_length_limits_output(self):
        self.assertEqual(sanitize_html("abcde", max_length=3), "abc")

    def test_non_string_returns_as_is(self):
        self.assertEqual(sanitize_html(123), 123)


class ValidateStringTests(TestCase):
    def test_required_missing_raises(self):
        with self.assertRaises(ValueError):
            validate_string("", required=True, field_name="الاسم")

    def test_none_optional_returns_empty(self):
        self.assertEqual(validate_string(None), "")

    def test_min_length_enforced(self):
        with self.assertRaises(ValueError):
            validate_string("abc", min_len=5, field_name="الكود")

    def test_max_length_truncates(self):
        self.assertEqual(validate_string("abcdef", max_len=3), "abc")


class ValidateEmailTests(TestCase):
    def test_valid_email(self):
        self.assertEqual(validate_email("user@example.com"), "user@example.com")

    def test_invalid_email_raises(self):
        with self.assertRaises(ValueError):
            validate_email("not-an-email")

    def test_empty_returns_empty(self):
        self.assertEqual(validate_email(""), "")


class ValidatePasswordStrengthTests(TestCase):
    def test_short_password_raises(self):
        with self.assertRaises(ValueError):
            validate_password_strength("short")

    def test_acceptable_password(self):
        self.assertEqual(validate_password_strength("password123"), "password123")


class SanitizeJsonBodyTests(TestCase):
    def test_nested_sanitization(self):
        body = {"name": "<script>x</script>", "items": ["<script>y</script>"], "n": 5}
        cleaned = sanitize_json_body(body)
        self.assertEqual(cleaned["name"], "&lt;script&gt;x&lt;/script&gt;")
        self.assertEqual(cleaned["items"], ["&lt;script&gt;y&lt;/script&gt;"])
        self.assertEqual(cleaned["n"], 5)
