import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Import functions from btc_bot
import btc_bot


class TestGetClient(unittest.TestCase):
    """Tests for the get_client function."""

    def test_get_client_with_valid_json(self):
        """Test that get_client correctly reads a valid JSON key file."""
        test_key = {
            "name": "organizations/test-org/apiKeys/test-key",
            "privateKey": "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEE...\n-----END EC PRIVATE KEY-----\n"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_key, f)
            temp_path = f.name

        try:
            with patch.dict(os.environ, {"COINBASE_API_JSON_PATH": temp_path}, clear=True):
                with patch('btc_bot.RESTClient') as mock_client:
                    mock_client.return_value = MagicMock()
                    client = btc_bot.get_client()
                    mock_client.assert_called_once_with(
                        api_key="organizations/test-org/apiKeys/test-key",
                        api_secret="-----BEGIN EC PRIVATE KEY-----\nMHQCAQEE...\n-----END EC PRIVATE KEY-----\n"
                    )
        finally:
            os.unlink(temp_path)

    def test_get_client_missing_private_key(self):
        """Test that get_client raises error when privateKey is missing."""
        test_key = {"name": "organizations/test-org/apiKeys/test-key"}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_key, f)
            temp_path = f.name

        try:
            with patch.dict(os.environ, {"COINBASE_API_JSON_PATH": temp_path}, clear=True):
                with self.assertRaises(RuntimeError) as ctx:
                    btc_bot.get_client()
                self.assertIn("privateKey", str(ctx.exception))
        finally:
            os.unlink(temp_path)

    def test_get_client_invalid_json_path(self):
        """Test that get_client raises error for non-existent JSON file."""
        with patch.dict(os.environ, {"COINBASE_API_JSON_PATH": "/nonexistent/path.json"}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                btc_bot.get_client()
            self.assertIn("Cannot read JSON file", str(ctx.exception))


class TestGetCurrentPrice(unittest.TestCase):
    """Tests for the get_current_price function."""

    def test_get_current_price_success(self):
        """Test successful price fetching."""
        mock_client = MagicMock()
        mock_client.get_product.return_value = {"price": "91234.56"}

        price = btc_bot.get_current_price(mock_client, "BTC-USD")

        self.assertEqual(price, 91234.56)
        mock_client.get_product.assert_called_once_with("BTC-USD")

    def test_get_current_price_integer(self):
        """Test price fetching with integer price."""
        mock_client = MagicMock()
        mock_client.get_product.return_value = {"price": "90000"}

        price = btc_bot.get_current_price(mock_client, "BTC-USD")

        self.assertEqual(price, 90000.0)

    def test_get_current_price_missing_price(self):
        """Test error when price field is missing."""
        mock_client = MagicMock()
        mock_client.get_product.return_value = {}

        with self.assertRaises(KeyError):
            btc_bot.get_current_price(mock_client, "BTC-USD")


class TestPlaceLimitBuy(unittest.TestCase):
    """Tests for the place_limit_buy function."""

    def test_place_limit_buy_success(self):
        """Test successful order placement."""
        mock_client = MagicMock()
        mock_client.limit_order_gtc_buy.return_value = {
            "success": True,
            "success_response": {"order_id": "test-order-123"}
        }

        with patch('btc_bot.uuid.uuid4', return_value='test-uuid'):
            order_id = btc_bot.place_limit_buy(mock_client, "BTC-USD", 90000.0)

        self.assertEqual(order_id, "test-order-123")
        mock_client.limit_order_gtc_buy.assert_called_once()

    def test_place_limit_buy_failure(self):
        """Test failed order placement."""
        mock_client = MagicMock()
        mock_client.limit_order_gtc_buy.return_value = {
            "success": False,
            "error_response": {"message": "Insufficient funds"}
        }

        with patch('btc_bot.uuid.uuid4', return_value='test-uuid'):
            order_id = btc_bot.place_limit_buy(mock_client, "BTC-USD", 90000.0)

        self.assertIsNone(order_id)

    def test_place_limit_buy_calculates_correct_size(self):
        """Test that base_size is calculated correctly."""
        mock_client = MagicMock()
        mock_client.limit_order_gtc_buy.return_value = {
            "success": True,
            "success_response": {"order_id": "test-order"}
        }

        with patch('btc_bot.uuid.uuid4', return_value='test-uuid'):
            btc_bot.place_limit_buy(mock_client, "BTC-USD", 100000.0)

        # USD_TO_SPEND (100) / 100000 = 0.001 BTC
        call_args = mock_client.limit_order_gtc_buy.call_args
        self.assertEqual(call_args.kwargs["base_size"], "0.00100000")
        self.assertEqual(call_args.kwargs["limit_price"], "100000.00")


class TestMainLoop(unittest.TestCase):
    """Tests for main loop logic."""

    @patch('btc_bot.get_client')
    @patch('btc_bot.get_current_price')
    @patch('btc_bot.place_limit_buy')
    @patch('btc_bot.time.sleep', side_effect=KeyboardInterrupt)
    def test_main_does_not_buy_above_target(self, mock_sleep, mock_buy, mock_price, mock_client):
        """Test that no buy happens when price is above target."""
        mock_client.return_value = MagicMock()
        mock_price.return_value = 95000.0  # Above TARGET_PRICE (90000)

        with self.assertRaises(KeyboardInterrupt):
            btc_bot.main()

        mock_buy.assert_not_called()

    @patch('btc_bot.get_client')
    @patch('btc_bot.get_current_price')
    @patch('btc_bot.place_limit_buy')
    @patch('btc_bot.time.sleep', side_effect=KeyboardInterrupt)
    def test_main_buys_at_target(self, mock_sleep, mock_buy, mock_price, mock_client):
        """Test that buy happens when price equals target."""
        mock_client.return_value = MagicMock()
        mock_price.return_value = 90000.0  # Equals TARGET_PRICE
        mock_buy.return_value = "order-123"

        with self.assertRaises(KeyboardInterrupt):
            btc_bot.main()

        mock_buy.assert_called_once()

    @patch('btc_bot.get_client')
    @patch('btc_bot.get_current_price')
    @patch('btc_bot.place_limit_buy')
    @patch('btc_bot.time.sleep', side_effect=KeyboardInterrupt)
    def test_main_buys_below_target(self, mock_sleep, mock_buy, mock_price, mock_client):
        """Test that buy happens when price is below target."""
        mock_client.return_value = MagicMock()
        mock_price.return_value = 85000.0  # Below TARGET_PRICE
        mock_buy.return_value = "order-123"

        with self.assertRaises(KeyboardInterrupt):
            btc_bot.main()

        mock_buy.assert_called_once()


if __name__ == "__main__":
    unittest.main()