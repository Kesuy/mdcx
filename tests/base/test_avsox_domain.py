from mdcx.base.web import extract_avsox_domain


def test_extract_avsox_domain_skips_qr_generator_and_official_placeholder():
    html = """
    <img src="https://api.qrserver.com/v1/create-qr-code/?data=https://avsox.click">
    <a href="https://avsox.com">old domain</a>
    <a href="https://avsox.click/cn">current domain</a>
    """

    assert extract_avsox_domain(html) == "https://avsox.click"


def test_extract_avsox_domain_rejects_unrelated_urls():
    assert extract_avsox_domain('<script src="https://cdn.example.test/app.js"></script>') == ""
