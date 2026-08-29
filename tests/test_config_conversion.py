import json
from pathlib import Path

from mdcx.config.enums import DownloadableFile, FixedScrapingType, HDPicSource, KeepableFile, Website
from mdcx.config.migrations import CURRENT_CONFIG_VERSION
from mdcx.config.models import DEFAULT_FIELD_SITE_PRIORITY, Config
from mdcx.config.resource_policy import resource_policy
from mdcx.config.v1 import ConfigV1, load_v1
from mdcx.controllers.main_window.site_priority_dialog import (
    FIELD_PRIORITY_FIELDS,
    _sync_field_sites_after_type_sites_changed,
)
from mdcx.gen.field_enums import CrawlerResultFields
from tests.random_generator import generate_random_pydantic_instance


def generate_random_config() -> Config:
    """生成具有随机字段值的 Config 实例"""
    r = generate_random_pydantic_instance(
        Config,
        no_default=True,
        allow_default=[
            "website_set",
            "headless_browser_sites",
        ],
    )
    d = r.model_dump(mode="json")

    errors = []

    def dict_fields_all_different(d1: dict, d2: dict) -> bool:
        """
        递归检查两个字典是否所有字段都不相同.

        Returns:
            bool: 如果所有字段都不相同返回 True，否则返回 False
        """
        for key in d1:
            if key not in d2:  # 非共同字段, 视为不同
                continue

            value1 = d1[key]
            value2 = d2[key]

            # 如果值相同,返回 False
            if value1 == value2:
                errors.append(f"字段 '{key}' 的值相同: {value1}")
                return False

            # 如果都是字典,递归检查
            if isinstance(value1, dict) and isinstance(value2, dict):
                if not dict_fields_all_different(value1, value2):
                    return False

        return True

    # 检查任何字段都与默认值不相同
    # default = Config().model_dump(mode="json")
    # assert dict_fields_all_different(d, default), "生成的随机配置中存在与默认值相同的字段: " + ", ".join(errors)

    return Config.model_validate(d)


def test_config_default_keep_files_match_default_template():
    data = json.loads(Path("resources/config/default_config.json").read_text(encoding="utf-8"))
    Config.update(data)
    template_config = Config.model_validate(data)

    assert Config().keep_files == template_config.keep_files == [KeepableFile.TRAILER, KeepableFile.THEME_VIDEOS]


def test_resource_policy_exposes_download_and_keep_semantics():
    policy = resource_policy(
        DownloadableFile.POSTER,
        KeepableFile.POSTER,
        download_files=[DownloadableFile.POSTER],
        keep_files=[],
    )

    assert policy.should_download is True
    assert policy.should_keep is False
    assert policy.should_remove_existing is False

    remove_policy = resource_policy(
        DownloadableFile.POSTER,
        KeepableFile.POSTER,
        download_files=[],
        keep_files=[],
    )

    assert remove_policy.should_download is False
    assert remove_policy.should_keep is False
    assert remove_policy.should_remove_existing is True


def test_from_legacy():
    """测试从旧版配置转换为新版配置"""
    config_v1 = ConfigV1()
    config_v1.wuma_style = "test_value"
    config_v1.javdb_website = "https://test.com"  # type: ignore

    config = Config.from_legacy(config_v1.__dict__.copy())

    assert Website.JAVDB in config.site_configs
    assert config.get_site_url(Website.JAVDB) == "https://test.com"
    assert config.wuma_style == "test_value"
    assert config.folder_moword is True
    assert config.file_moword is True
    assert config.folder_hd is True
    assert config.file_hd is True


def test_legacy_ini_local_number_image_switch_round_trips(tmp_path: Path):
    ini_path = tmp_path / "legacy.ini"
    ini_path.write_text("[file_download]\nuse_local_number_images = false\n", encoding="utf-8")

    data, errors = load_v1(ini_path)
    config = ConfigV1(**data).to_pydantic_model()

    assert errors == []
    assert config.use_local_number_images is False


def test_legacy_ini_without_local_number_image_switch_keeps_compatible_default():
    config = ConfigV1().to_pydantic_model()

    assert config.use_local_number_images is True


def test_removed_fc2cmadb_auto_login_config_is_ignored_while_cookie_is_preserved():
    config = Config.model_validate(
        {
            "fc2ppvdb": "fc2cmadb-session=manual-cookie",
            "fc2cmadb_auth_mode": "auto",
            "fc2cmadb_password": "obsolete-password",
        }
    )
    dumped = config.model_dump(mode="json")

    assert config.fc2ppvdb == "fc2cmadb-session=manual-cookie"
    assert "fc2cmadb_auth_mode" not in dumped
    assert "fc2cmadb_password" not in dumped


def test_legacy_ini_auto_login_mode_is_accepted_and_dropped(tmp_path: Path):
    ini_path = tmp_path / "legacy-fc2cmadb.ini"
    ini_path.write_text(
        "[cookies]\nfc2ppvdb = fc2cmadb-session=manual-cookie\nfc2cmadb_auth_mode = auto\n",
        encoding="utf-8",
    )

    data, errors = load_v1(ini_path)
    config = ConfigV1(**data).to_pydantic_model()

    assert errors == []
    assert config.fc2ppvdb == "fc2cmadb-session=manual-cookie"
    assert "fc2cmadb_auth_mode" not in config.model_dump()


def test_config_update_removes_old_youma_poster_option_without_enabling_new_option():
    data = {"download_files": ["poster", "youma_use_poster"]}

    Config.update(data)
    config = Config.model_validate(data)

    assert DownloadableFile.POSTER_AUTO_BEST not in config.download_files
    assert "youma_use_poster" not in config.model_dump(mode="json")["download_files"]


def test_config_builds_type_field_priority_from_legacy_field_configs():
    data = {
        "website_youma": ["dmm", "javdb"],
        "field_configs": {
            "title": {
                "site_prority": ["javdb", "dmm", "javbus"],
                "language": "jp",
                "translate": True,
            }
        },
    }

    Config.update(data)
    config = Config.model_validate(data)

    assert config.website_youma == [Website.DMM, Website.JAVDB]
    assert config.get_type_field_config(FixedScrapingType.YOUMA, CrawlerResultFields.TITLE).site_prority == [
        Website.JAVDB,
        Website.DMM,
    ]


def test_config_default_site_priorities_follow_current_frontend_defaults():
    config = Config()

    assert config.website_youma == [
        Website.MGSTAGE,
        Website.OFFICIAL,
        Website.MISSAV,
        Website.JAVBUS,
        Website.JAVDBAPI,
        Website.JAV321,
        Website.DMM,
        Website.AVBASE,
    ]
    assert config.website_wuma == [Website.MISSAV, Website.MMTV, Website.AVSOX]
    assert config.website_suren == [
        Website.MGSTAGE,
        Website.JAVBUS,
        Website.JAV321,
        Website.DMM,
        Website.AVBASE,
        Website.MMTV,
    ]
    assert config.website_fc2 == [
        Website.FC2PPVDB,
        Website.FC2,
        Website.MMTV,
        Website.FC2HUB,
        Website.FC2CLUB,
    ]
    assert config.website_oumei == [Website.THEPORNDB]
    assert config.website_guochan == [
        Website.CNMDB,
        Website.HDOUBAN,
        Website.MADOUQU,
        Website.JAVDAY,
        Website.MDTV,
    ]
    assert config.get_field_config(CrawlerResultFields.TITLE).site_prority == DEFAULT_FIELD_SITE_PRIORITY
    assert config.get_type_field_config(FixedScrapingType.YOUMA, CrawlerResultFields.TITLE).site_prority == [
        Website.DMM,
        Website.OFFICIAL,
        Website.MGSTAGE,
        Website.AVBASE,
        Website.JAV321,
        Website.JAVBUS,
        Website.MISSAV,
    ]
    assert config.get_type_field_config(FixedScrapingType.FC2, CrawlerResultFields.TITLE).site_prority == [
        Website.FC2PPVDB,
        Website.MMTV,
        Website.FC2HUB,
        Website.FC2,
    ]


def test_version_2_config_enables_fc2cmadb_first_without_reordering_other_fc2_sites():
    data = {
        "config_version": 2,
        "website_fc2": ["fc2hub", "fc2", "fc2club"],
        "field_configs": {
            "title": {
                "site_prority": ["fc2hub", "fc2", "fc2club"],
                "language": "undefined",
                "translate": True,
            }
        },
        "type_field_configs": {
            "fc2": {
                "title": {"site_prority": ["fc2hub", "fc2"]},
            }
        },
    }

    Config.update(data)
    config = Config.model_validate(data)

    assert config.config_version == 4
    assert config.website_fc2 == [Website.FC2PPVDB, Website.FC2HUB, Website.FC2, Website.FC2CLUB]
    assert config.get_type_field_config(FixedScrapingType.FC2, CrawlerResultFields.TITLE).site_prority == [
        Website.FC2PPVDB,
        Website.FC2HUB,
        Website.FC2,
    ]


def test_version_3_config_preserves_explicit_fc2cmadb_removal():
    data = {
        "config_version": 3,
        "website_fc2": ["fc2hub", "fc2"],
    }

    Config.update(data)
    config = Config.model_validate(data)

    assert config.website_fc2 == [Website.FC2HUB, Website.FC2]


def test_removed_hd_pic_sources_are_filtered_from_old_config():
    data = {
        "download_hd_pics": [
            "poster",
            "thumb",
            "amazon",
            "official",
            "google",
            "goo_only",
        ],
        "google_used": ["m.media-amazon.com"],
        "google_exclude": ["fake"],
        "config_version": 1,
    }

    Config.update(data)
    config = Config.model_validate(data)

    assert config.download_hd_pics == [HDPicSource.AMAZON]
    assert config.config_version == CURRENT_CONFIG_VERSION
    assert "google_used" not in data
    assert "google_exclude" not in data


def test_old_config_gets_default_amazon_strict_pic_verify():
    data = {"config_version": 1}

    Config.update(data)
    config = Config.model_validate(data)

    assert config.amazon_skip_poster_size_precheck is False
    assert config.amazon_strict_pic_verify is False
    assert config.field_priority_try_all_images is False


def test_frontend_field_priority_fields_include_legacy_configurable_fields():
    assert CrawlerResultFields.ORIGINALTITLE in FIELD_PRIORITY_FIELDS
    assert CrawlerResultFields.ORIGINALPLOT in FIELD_PRIORITY_FIELDS
    assert CrawlerResultFields.ALL_ACTORS in FIELD_PRIORITY_FIELDS


def test_sync_field_sites_after_type_sites_changed_preserves_field_order():
    assert _sync_field_sites_after_type_sites_changed(
        [Website.JAVDB, Website.DMM],
        [Website.DMM, Website.JAVDB, Website.JAVBUS],
        [Website.JAVBUS, Website.JAVDB, Website.MGSTAGE, Website.DMM],
    ) == [Website.JAVDB, Website.DMM, Website.MGSTAGE]


def test_default_config_template_is_valid_json_and_matches_current_model():
    template_path = Path("resources/config/default_config.json")
    template = json.loads(template_path.read_text(encoding="utf-8"))

    config = Config.model_validate(template)

    assert config.media_path == "D:\\Media\\Input"
    assert config.softlink_path == "X:\\Media\\Softlink"
    assert config.failed_output_folder == "D:\\Media\\Input\\failed"
    assert config.amazon_skip_poster_size_precheck is False
    assert config.amazon_strict_pic_verify is False
    assert config.field_priority_try_all_images is False
    assert config.website_youma == Config().website_youma
    assert config.get_field_config(CrawlerResultFields.TITLE).site_prority == DEFAULT_FIELD_SITE_PRIORITY
    for field in CrawlerResultFields:
        assert config.get_field_config(field) == Config().get_field_config(field)


def test_builtin_naming_templates_are_migrated_to_jinja2_syntax():
    data = {
        "folder_name": "letters/number",
        "naming_file": "number",
        "naming_media": "[number]title",
        "update_a_folder": "actor",
        "update_b_folder": "number actor",
        "update_c_filetemplate": "number",
        "update_d_folder": "number actor",
        "update_titletemplate": "number title",
    }

    Config.update(data)

    assert data["folder_name"] == "{{ letters }}/{{ number }}"
    assert data["naming_file"] == "{{ number }}"
    assert data["naming_media"] == "[{{ number }}]{% if title and title != number %}{{ title }}{% endif %}"
    assert data["update_a_folder"] == "{{ actor }}"
    assert data["update_b_folder"] == "{{ number }} {{ actor }}"
    assert data["update_c_filetemplate"] == "{{ number }}"
    assert data["update_d_folder"] == "{{ number }} {{ actor }}"
    assert data["update_titletemplate"] == "{{ number }} {{ title }}"
    Config.model_validate(data)


def test_braced_naming_templates_are_migrated_to_jinja2_syntax():
    data = {
        "naming_file": "{number}{?studio: [{studio}]} {definition}",
    }

    Config.update(data)

    assert data["naming_file"] == "{{ number }}{% if studio %} [{{ studio }}]{% endif %} {{ definition }}"
    Config.model_validate(data)
