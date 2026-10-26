import pytest

from bank_faqs import tools


@pytest.mark.parametrize('name, expected', [
    ('BIDV', 'BIDV'),
    ('vcb', 'Vietcombank'),
    ('Vietin', 'VietinBank'),
    ('mb bank', 'MBBank'),
    ('Bắc Á', 'Bắc Á Bank'),
    ('bac a bank', 'Bắc Á Bank'),
    ('ngân hàng Techcom', 'Techcombank'),
    ('Ngân hàng Nam Á', 'Nam Á Bank'),
    ('nông nghiệp', 'Agribank'),
    ('acb', 'ACB'),
])
def test_find_bank(name, expected):
    assert list(tools._find_bank(tools._rates(), name)['Mã NH']) == [expected]


@pytest.mark.parametrize('name', ['a', 'ab', 'TPBank', 'xyz'])
def test_find_bank_not_found(name):
    assert tools._find_bank(tools._rates(), name).empty


def test_norm():
    assert tools._norm('Ngân hàng Đông Á!') == 'nganhangdonga'


def test_interest_rate_one_bank():
    out = tools.get_interest_rate.invoke({'bank': 'BIDV'})
    assert out.startswith('BIDV (cập nhật 23/10/2026')
    assert 'Online: 1T 4.8%, 3T 4.8%, 6T 7.2%, 12T 7.4%' in out
    assert 'Tại quầy: 1T 2.1%' in out


def test_interest_rate_missing_terms():
    assert '18T không có' in tools.get_interest_rate.invoke({'bank': 'Sacombank'})


def test_interest_rate_all_banks():
    out = tools.get_interest_rate.invoke({})
    lines = out.splitlines()
    assert lines[0] == 'Lãi suất tiết kiệm online (%/năm), cập nhật 23/10/2026:'
    assert len(lines) == 1 + 17
    assert 'SHB: 1T 4.75%, 3T 4.75%, 6T 7.7%, 12T 7.8%' in out


def test_interest_rate_unknown_bank_lists_available():
    out = tools.get_interest_rate.invoke({'bank': 'TPBank'})
    assert "Không có dữ liệu lãi suất của 'TPBank'" in out
    assert 'Vietcombank' in out


def test_search_faq_handles_backend_error(monkeypatch):
    def boom():
        raise ConnectionError('qdrant down')
    monkeypatch.setattr(tools, '_retriever', boom)
    out = tools.search_faq.invoke({'query': 'quên mật khẩu'})
    assert out.startswith('Lỗi hệ thống khi tra cứu dữ liệu nội bộ (ConnectionError)')


def test_web_search_handles_backend_error(monkeypatch):
    def boom(*args, **kwargs):
        raise TimeoutError()
    monkeypatch.setattr(tools.tavily_client, 'search', boom)
    out = tools.web_search.invoke({'query': 'lãi suất'})
    assert out.startswith('Lỗi hệ thống khi tìm kiếm trên web (TimeoutError)')
