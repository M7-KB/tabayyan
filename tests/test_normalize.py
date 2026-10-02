"""Synthetic non-scriptural fixtures for matching normalization."""

import unittest

from corpus.normalize import normalize_arabic


class NormalizerTests(unittest.TestCase):
    def test_diacritics_and_tatweel(self):
        self.assertEqual(normalize_arabic("مَكْتَـبٌ"), "مكتب")

    def test_variants(self):
        self.assertEqual(normalize_arabic("أ إ آ ٱ ى ة"), "ا ا ا ا ي ه")

    def test_decomposed_alef(self):
        for value in ("أ", "ا\u0654", "إ", "ا\u0655", "آ", "ا\u0653"):
            with self.subTest(value=value):
                self.assertEqual(normalize_arabic(value), "ا")

    def test_whitespace_and_empty(self):
        self.assertEqual(normalize_arabic("  مكتب\t\n جديد\u00a0 "), "مكتب جديد")
        self.assertEqual(normalize_arabic(""), "")
        self.assertEqual(normalize_arabic("\t \n"), "")
        self.assertEqual(normalize_arabic("ـَ"), "")

    def test_preserves_non_arabic_accents_numbers_punctuation_and_hamza(self):
        value = "café 123 ١٢٣، ء ؤ ئ ﷺ ﷲ"
        self.assertEqual(normalize_arabic(value), value)

    def test_extended_marks_and_small_letters(self):
        self.assertEqual(normalize_arabic("ب\u0610\u0670\u06d6\u08f0\u0898"), "ب")
        self.assertEqual(normalize_arabic("\u06e5\u06e6"), "\u06e5\u06e6")

    def test_idempotent_for_every_unicode_scalar(self):
        # A deterministic Unicode-wide check catches interactions missed by examples.
        for start in range(0, 0x110000, 1024):
            text = "".join(
                chr(code)
                for code in range(start, min(start + 1024, 0x110000))
                if not 0xD800 <= code <= 0xDFFF
            )
            normalized = normalize_arabic(text)
            self.assertEqual(normalize_arabic(normalized), normalized, f"block {start:x}")

    def test_preserves_word_and_punctuation_boundaries(self):
        self.assertNotEqual(normalize_arabic("مكتب جديد"), normalize_arabic("مكتبجديد"))
        self.assertNotEqual(normalize_arabic("مكتب، جديد"), normalize_arabic("مكتب جديد"))

    def test_idempotent_when_removing_marks_exposes_composition(self):
        for text in ("a\u064e\u030a", "eـ\u0301", "ب\u064e\u0654"):
            normalized = normalize_arabic(text)
            self.assertEqual(normalize_arabic(normalized), normalized)
        self.assertEqual(normalize_arabic("a\u064e\u030a"), "å")

    def test_does_not_change_source(self):
        source = "مَدْرَسَةٌ"
        self.assertEqual(normalize_arabic(source), "مدرسه")
        self.assertEqual(source, "مَدْرَسَةٌ")

    def test_rejects_non_string(self):
        for value in (None, 123, b"text", ["text"]):
            with self.subTest(value=value), self.assertRaises(TypeError):
                normalize_arabic(value)


if __name__ == "__main__":
    unittest.main()
