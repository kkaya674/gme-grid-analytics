import pytest
import pandas as pd
from gme_api.client import GMEClient
from gme_api.utils import flatten_gme_response

def test_client_init():
    client = GMEClient("user", "pass")
    assert client.username == "user"
    assert client.password == "pass"
    assert client.token is None

def test_flatten_empty_data():
    df = flatten_gme_response(None)
    assert isinstance(df, pd.DataFrame)
    assert df.empty

def test_flatten_list_data():
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    df = flatten_gme_response(data)
    assert len(df) == 2
    assert "a" in df.columns

@pytest.fixture
def mock_client(mocker):
    client = GMEClient("user", "pass")
    mocker.patch.object(client, 'login', return_value=True)
    client.token = "fake_jwt"
    return client

def test_fetch_data_mock(mock_client, mocker):
    mock_response = {"ContentResponse": "fake_b64"}
    mocker.patch.object(mock_client, 'make_request', return_value=mock_response)
    mocker.patch.object(mock_client, 'decode_response', return_value=[{"price": 10}])
    
    data = mock_client.fetch_data("ME_ZonalPrices", "MGP", 20240101, 20240101)
    assert data == [{"price": 10}]
