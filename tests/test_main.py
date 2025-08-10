import pytest
from unittest.mock import Mock, AsyncMock, patch
from main import create_client, run_server, main


class TestMain:
    @pytest.mark.asyncio
    @patch('main.login_as_account')
    @patch('main.login_as_bots')
    @patch('main.Client.create')
    async def test_create_client_with_account(self, mock_client_create, mock_login_bots, mock_login_account):
        # Setup mocks
        mock_config = Mock()
        mock_config.telegram.account = Mock()  # Account is configured
        
        mock_account = Mock()
        mock_bots = [Mock()]
        mock_client = Mock()
        
        mock_login_account.return_value = mock_account
        mock_login_bots.return_value = mock_bots
        mock_client_create.return_value = mock_client
        
        # Call function
        result = await create_client(mock_config)
        
        # Assertions
        mock_login_account.assert_called_once_with(mock_config)
        mock_login_bots.assert_called_once_with(mock_config)
        mock_client_create.assert_called_once_with(mock_bots, mock_account)
        assert result == mock_client

    @pytest.mark.asyncio
    @patch('main.login_as_account')
    @patch('main.login_as_bots')
    @patch('main.Client.create')
    async def test_create_client_without_account(self, mock_client_create, mock_login_bots, mock_login_account):
        # Setup mocks
        mock_config = Mock()
        mock_config.telegram.account = None  # No account configured
        
        mock_bots = [Mock()]
        mock_client = Mock()
        
        mock_login_bots.return_value = mock_bots
        mock_client_create.return_value = mock_client
        
        # Call function
        result = await create_client(mock_config)
        
        # Assertions
        mock_login_account.assert_not_called()
        mock_login_bots.assert_called_once_with(mock_config)
        mock_client_create.assert_called_once_with(mock_bots, None)
        assert result == mock_client

    @pytest.mark.asyncio
    @patch('main.Server')
    @patch('main.UvicornConfig')
    @patch('main.logging.getLogger')
    async def test_run_server(self, mock_get_logger, mock_uvicorn_config, mock_server_class):
        # Setup mocks
        mock_app = Mock()
        mock_logger = Mock()
        mock_config = Mock()
        mock_server = Mock()
        mock_server.serve = AsyncMock()
        
        mock_get_logger.return_value = mock_logger
        mock_uvicorn_config.return_value = mock_config
        mock_server_class.return_value = mock_server
        
        # Call function
        await run_server(mock_app, "localhost", 8080, "Test Server")
        
        # Assertions
        mock_logger.info.assert_called_once_with("Starting Test Server server on localhost:8080")
        mock_uvicorn_config.assert_called_once_with(
            mock_app,
            host="localhost",
            port=8080,
            loop="none",
            log_level="info",
        )
        mock_server_class.assert_called_once_with(config=mock_config)
        mock_server.serve.assert_called_once()

    @pytest.mark.asyncio
    @patch('main.get_config')
    @patch('main.create_client')
    @patch('main.create_app')
    @patch('main.run_server')
    async def test_main(self, mock_run_server, mock_create_app, mock_create_client, mock_get_config):
        # Setup mocks
        mock_config = Mock()
        mock_config.tgfs.server.host = "0.0.0.0"
        mock_config.tgfs.server.port = 9000
        
        mock_client = Mock()
        mock_app = Mock()
        
        mock_get_config.return_value = mock_config
        mock_create_client.return_value = mock_client
        mock_create_app.return_value = mock_app
        mock_run_server.return_value = None
        
        # Call function
        await main()
        
        # Assertions
        mock_get_config.assert_called_once()
        mock_create_client.assert_called_once_with(mock_config)
        mock_create_app.assert_called_once_with(mock_client, mock_config)
        mock_run_server.assert_called_once_with(mock_app, "0.0.0.0", 9000, "TGFS")
