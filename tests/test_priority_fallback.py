import unittest
from unittest.mock import Mock, patch

import app.predictor as predictor


class PriorityFallbackTests(unittest.TestCase):
    def setUp(self):
        self.original_vectorizer = predictor._vectorizer
        self.original_cat_model = predictor._cat_model
        self.original_prio_model = predictor._prio_model

        predictor._vectorizer = Mock()
        predictor._cat_model = Mock()
        predictor._prio_model = Mock()

        predictor._vectorizer.transform.return_value = [[0, 1]]
        predictor._cat_model.predict.return_value = ["Technical Support"]
        predictor._cat_model.predict_proba.return_value = [[0.80]]
        predictor._prio_model.predict.return_value = ["Low"]
        predictor._prio_model.predict_proba.return_value = [[0.55]]

    def tearDown(self):
        predictor._vectorizer = self.original_vectorizer
        predictor._cat_model = self.original_cat_model
        predictor._prio_model = self.original_prio_model

    def test_uses_gemini_priority_when_rf_confidence_is_low(self):
        with patch("app.predictor.gemini_classify_priority", return_value={"priority": "High", "reason": "Serious issue"}) as gemini_mock:
            result = predictor.predict_complaint("My internet service is down and I cannot work")

        self.assertEqual(result["priority"], "High")
        self.assertEqual(result["priority_confidence"], 0.55)
        self.assertEqual(result["handled_by"], "Random Forest")
        gemini_mock.assert_called_once()

    def test_keeps_rf_priority_when_gemini_fallback_fails(self):
        with patch("app.predictor.gemini_classify_priority", side_effect=RuntimeError("gemini unavailable")) as gemini_mock:
            result = predictor.predict_complaint("I need help with my billing")

        self.assertEqual(result["priority"], "Low")
        self.assertEqual(result["priority_confidence"], 0.55)
        self.assertEqual(result["handled_by"], "Random Forest")
        gemini_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
