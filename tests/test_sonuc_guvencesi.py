from sonuc_guvencesi import jsonl_denetle, sonuc_jsonl_mi


def test_sadece_sonuc_jsonl_dosyalarini_secer():
    assert sonuc_jsonl_mi("sonuc/test2000-ozet.jsonl")
    assert sonuc_jsonl_mi("sonuc/eval115-ozet.jsonl")
    assert sonuc_jsonl_mi("sonuc/valid300-ozet.jsonl")
    assert not sonuc_jsonl_mi("veri/test.jsonl")
    assert not sonuc_jsonl_mi("sonuc/test-ozet.json")


def test_toplu_ozet_kaydi_gecer():
    icerik = '{"n": 115, "f1": 0.12, "split": "eval115"}\n'
    assert jsonl_denetle("sonuc/eval115-ozet.jsonl", icerik) == []


def test_satir_duzeyindeki_alanlar_reddedilir_degerler_yazdirilmaz():
    icerik = '{"id": "synthetic-id", "gercek": "synthetic-gold", "tahmin": "synthetic-prediction"}\n'
    hatalar = jsonl_denetle("sonuc/test-sentetik.jsonl", icerik)
    assert len(hatalar) == 1
    assert "satır düzeyinde" in hatalar[0]
    assert "synthetic-id" not in hatalar[0]
    assert "synthetic-gold" not in hatalar[0]
    assert "synthetic-prediction" not in hatalar[0]


def test_gercek_ad_alani_da_reddedilir():
    icerik = '{"id": "synthetic-id", "gercek_ad": "synthetic-gold"}\n'
    assert jsonl_denetle("sonuc/test-sentetik.jsonl", icerik)


def test_hatalı_jsonl_fail_closed():
    assert jsonl_denetle("sonuc/test-sentetik.jsonl", "not-json\n")


def test_nesne_olmayan_jsonl_kaydi_fail_closed():
    assert jsonl_denetle("sonuc/test-sentetik.jsonl", '["synthetic"]\n')


def test_dogrulama_satiri_da_satir_duzeyiyse_reddedilir():
    icerik = '{"id": "synthetic-id", "gercek": "synthetic-gold"}\n'
    assert jsonl_denetle("sonuc/valid300-sentetik.jsonl", icerik)


def _git(cwd, *args):
    import subprocess

    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _git_repo(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _git(tmp_path, "config", "user.name", "synthetic-test")
    _git(tmp_path, "config", "user.email", "synthetic-test@example.invalid")
    sonuc = tmp_path / "sonuc"
    sonuc.mkdir()
    (sonuc / "test-ozet.jsonl").write_text('{"n": 1, "f1": 0.1}\n', encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "base")
    return _git_sha(tmp_path)


def _git_sha(tmp_path):
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_git_farki_yeni_kimlikli_satiri_yakalar(tmp_path, monkeypatch):
    from sonuc_guvencesi import git_denetle

    taban = _git_repo(tmp_path)
    (tmp_path / "sonuc" / "test-ozet.jsonl").write_text(
        '{"id": "synthetic-id", "gercek": "synthetic-gold"}\n', encoding="utf-8"
    )
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "row-level fixture")
    bas = _git_sha(tmp_path)
    monkeypatch.chdir(tmp_path)

    hatalar, sayi = git_denetle(taban, bas)

    assert sayi == 1
    assert len(hatalar) == 1


def test_git_farki_aggregate_jsonl_kaydini_kabul_eder(tmp_path, monkeypatch):
    from sonuc_guvencesi import git_denetle

    taban = _git_repo(tmp_path)
    (tmp_path / "sonuc" / "test-ozet.jsonl").write_text('{"n": 1, "f1": 0.2}\n', encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "aggregate fixture")
    bas = _git_sha(tmp_path)
    monkeypatch.chdir(tmp_path)

    hatalar, sayi = git_denetle(taban, bas)

    assert sayi == 1
    assert hatalar == []
