"""Regression tests for crash-prevention changes (no model download required)."""
import os
import tempfile
import unittest
from unittest.mock import patch, Mock

import speech
import auth
import runtime_compat


class StabilitySmokeTests(unittest.TestCase):
    def test_whisper_is_not_loaded_on_import(self):
        # A model should not be initialized just to open the teacher dashboard.
        self.assertNotIn("model", vars(speech))

    def test_transcription_preserves_output_and_cleans_audio(self):
        fake_model = Mock()
        fake_model.transcribe.return_value = {"text": " Bonjour à tous. "}
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio:
            path = audio.name
            audio.write(b"test")
        try:
            with patch.object(speech, "load_model", return_value=fake_model):
                self.assertEqual(
                    speech.transcribe_audio_file(path, cleanup=True),
                    "Bonjour à tous.",
                )
            self.assertFalse(os.path.exists(path))
            fake_model.transcribe.assert_called_once_with(
                path, language="fr", fp16=False
            )
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_failed_transcription_also_cleans_audio(self):
        fake_model = Mock()
        fake_model.transcribe.side_effect = RuntimeError("Test error")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio:
            path = audio.name
        try:
            with (
                patch.object(speech, "load_model", return_value=fake_model),
                patch.object(speech.st, "error"),
            ):
                self.assertEqual(
                    speech.transcribe_audio_file(path, cleanup=True), ""
                )
            self.assertFalse(os.path.exists(path))
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_teacher_clients_are_scoped_per_session(self):
        first_session, second_session = {}, {}
        with (
            patch.object(auth, "SUPABASE_URL", "https://example.supabase.co"),
            patch.object(auth, "SUPABASE_KEY", "test-publishable-key"),
            patch.object(auth, "create_client", side_effect=lambda *a: Mock()) as maker,
        ):
            with patch.object(auth.st, "session_state", first_session):
                first = auth.get_session_supabase()
                self.assertIs(auth.get_session_supabase(), first)
            with patch.object(auth.st, "session_state", second_session):
                second = auth.get_session_supabase()
                self.assertIsNot(second, first)
            self.assertEqual(maker.call_count, 2)


    def test_espeak_library_discovery_on_all_desktop_platforms(self):
        mac_lib = runtime_compat.find_espeak_library(
            system="Darwin",
            environ={},
            is_file=lambda path: path == "/opt/homebrew/lib/libespeak-ng.dylib",
        )
        self.assertEqual(mac_lib, "/opt/homebrew/lib/libespeak-ng.dylib")

        windows_lib = runtime_compat.find_espeak_library(
            system="Windows",
            environ={"ProgramFiles": "C:\\Program Files"},
            is_file=lambda path: path.endswith("libespeak-ng.dll"),
        )
        self.assertTrue(windows_lib.endswith("libespeak-ng.dll"))

        linux_default = runtime_compat.find_espeak_library(
            system="Linux",
            environ={},
            is_file=lambda path: False,
        )
        self.assertIsNone(linux_default)

    def test_explicit_library_location_takes_precedence(self):
        custom = "/custom/native/espeak-library"
        detected = runtime_compat.find_espeak_library(
            system="Windows",
            environ={"PHONEMIZER_ESPEAK_LIBRARY": custom},
            is_file=lambda path: False,
        )
        self.assertEqual(detected, custom)
        wrapper = Mock()
        runtime_compat.configure_espeak_library(
            wrapper,
            system="Linux",
            environ={"PHONEMIZER_ESPEAK_LIBRARY": custom},
        )
        wrapper.set_library.assert_called_once_with(custom)



if __name__ == "__main__":
    unittest.main()
