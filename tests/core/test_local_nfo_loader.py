from pathlib import Path

import pytest

from mdcx.core.local_nfo_loader import LocalNfoLoadError, load_local_nfo


def _write_nfo(path: Path, *, number: str = "H4610-ORI696", actor: str = "望月奈々") -> None:
    path.write_text(
        f"""<movie>
<title>{number} 望月 奈々</title>
<originaltitle>望月 奈々</originaltitle>
<num>{number}</num>
<actor><name>{actor}</name></actor>
<plot>简介</plot>
<year>2010</year>
</movie>""",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_load_local_nfo_reads_matching_video_metadata_and_images(tmp_path: Path):
    folder = tmp_path / "H4610-ORI696 望月 奈々 望月奈々"
    folder.mkdir()
    movie = folder / "H4610-ORI696 望月奈々.wmv"
    movie.write_bytes(b"movie")
    nfo = movie.with_suffix(".nfo")
    _write_nfo(nfo)
    for name in ("poster.jpg", "fanart.jpg", "thumb.jpg"):
        (folder / name).write_bytes(name.encode())

    loaded = await load_local_nfo(nfo)

    assert loaded.primary.file_info.file_path == movie
    assert loaded.primary.data.number == "H4610-ORI696"
    assert loaded.primary.data.actor == "望月奈々"
    assert loaded.primary.other.poster_path == folder / "poster.jpg"
    assert loaded.primary.other.fanart_path == folder / "fanart.jpg"
    assert loaded.primary.other.thumb_path == folder / "thumb.jpg"
    assert len(loaded.entries) == 1


@pytest.mark.asyncio
async def test_load_local_nfo_discovers_related_multi_cd_entries(tmp_path: Path):
    folder = tmp_path / "movie"
    folder.mkdir()
    nfo_paths = []
    for part in (1, 2):
        movie = folder / f"H4610-ORI696-CD{part}.mp4"
        movie.write_bytes(b"movie")
        nfo = movie.with_suffix(".nfo")
        _write_nfo(nfo)
        nfo_paths.append(nfo)

    loaded = await load_local_nfo(nfo_paths[0])

    assert [entry.file_info.cd_part for entry in loaded.entries] == ["-cd1", "-cd2"]
    assert loaded.primary.file_info.file_path.name == "H4610-ORI696-CD1.mp4"


@pytest.mark.asyncio
async def test_load_local_nfo_rejects_ambiguous_folder_without_matching_video(tmp_path: Path):
    nfo = tmp_path / "UNKNOWN.nfo"
    _write_nfo(nfo, number="UNKNOWN-999")
    (tmp_path / "AAA-001.mp4").write_bytes(b"a")
    (tmp_path / "BBB-002.mp4").write_bytes(b"b")

    with pytest.raises(LocalNfoLoadError, match="无法确定"):
        await load_local_nfo(nfo)


@pytest.mark.asyncio
async def test_load_local_nfo_does_not_merge_another_same_number_cd_group(tmp_path: Path):
    selected_nfo = None
    for prefix in ("edition-a", "edition-b"):
        for part in (1, 2):
            movie = tmp_path / f"H4610-ORI696 {prefix}-CD{part}.mp4"
            movie.write_bytes(b"movie")
            nfo = movie.with_suffix(".nfo")
            _write_nfo(nfo)
            if prefix == "edition-a" and part == 1:
                selected_nfo = nfo

    loaded = await load_local_nfo(selected_nfo)

    assert [entry.file_info.file_path.name for entry in loaded.entries] == [
        "H4610-ORI696 edition-a-CD1.mp4",
        "H4610-ORI696 edition-a-CD2.mp4",
    ]


@pytest.mark.asyncio
async def test_load_local_nfo_uses_distinct_keys_for_same_number_in_different_folders(tmp_path: Path):
    show_names = []
    for folder_name in ("first", "second"):
        folder = tmp_path / folder_name
        folder.mkdir()
        movie = folder / "H4610-ORI696.mp4"
        movie.write_bytes(b"movie")
        nfo = movie.with_suffix(".nfo")
        _write_nfo(nfo)
        show_names.append((await load_local_nfo(nfo)).primary.show_name)

    assert show_names[0] != show_names[1]
