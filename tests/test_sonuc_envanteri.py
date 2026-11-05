import subprocess

from sonuc_envanteri import _siniflandir, envanteri_uret, main, rapor_metni


def _git(kok, *args):
    subprocess.run(["git", *args], cwd=kok, check=True, capture_output=True, text=True)


def _depo(kok):
    subprocess.run(["git", "init", "-q"], cwd=kok, check=True)
    _git(kok, "config", "user.name", "synthetic-test")
    _git(kok, "config", "user.email", "synthetic-test@example.invalid")
    sonuc = kok / "sonuc"
    sonuc.mkdir()
    (sonuc / "satir.jsonl").write_text(
        '{"id":"synthetic-id","gercek":"synthetic-gold","tahmin":"synthetic-prediction"}\n',
        encoding="utf-8",
    )
    (sonuc / "olcum.jsonl").write_text(
        '{"adim":1,"eval_loss":0.4,"f1":0.2,"model":"synthetic","n":8}\n',
        encoding="utf-8",
    )
    (sonuc / "belirsiz.jsonl").write_text('{"not":"synthetic-value"}\n', encoding="utf-8")
    (sonuc / "bozuk.jsonl").write_text("not-json\n", encoding="utf-8")
    _git(kok, "add", ".")
    _git(kok, "commit", "-m", "synthetic inventory fixture")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=kok, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_envanter_sadece_sinif_sayilarini_dondurur(tmp_path):
    ref = _depo(tmp_path)

    sayim = envanteri_uret(ref, tmp_path)

    assert sayim == {"dosya": 4, "satir_duzeyi": 1, "toplu": 1, "belirsiz": 2}


def test_rapor_dosya_adi_ve_satir_degerlerini_yayimlamaz(tmp_path):
    ref = _depo(tmp_path)
    metin = rapor_metni(ref, envanteri_uret(ref, tmp_path))

    assert "satır.jsonl" not in metin
    assert "synthetic-id" not in metin
    assert "synthetic-gold" not in metin
    assert "synthetic-prediction" not in metin
    assert "synthetic-value" not in metin
    assert "satır_düzeyi=1" in metin
    assert "toplu=1" in metin
    assert "belirsiz=2" in metin


def test_sonraki_satirdaki_satir_duzeyi_kayit_dosyayi_isaretler(tmp_path):
    _depo(tmp_path)
    yol = tmp_path / "sonuc" / "sonraki-satir.jsonl"
    yol.write_text('{"n":1,"f1":0.2}\n{"id":"synthetic-id"}\n', encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "second-line fixture")
    ref = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()

    sayim = envanteri_uret(ref, tmp_path)

    assert sayim["satir_duzeyi"] == 2
    assert sayim["toplu"] == 1


def test_nested_english_row_level_alias_is_classified():
    icerik = '{"records":[{"metadata":{"Prediction":"synthetic-value"}}]}'
    assert _siniflandir(icerik) == "satir_duzeyi"


def test_strict_belirsiz_ve_satir_duzeyi_dosyada_basarisiz(tmp_path, monkeypatch, capsys):
    ref = _depo(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert main(["--ref", ref, "--strict"]) == 1
    cikti = capsys.readouterr()
    assert "satır_düzeyi=1" in cikti.out
    assert "belirsiz=2" in cikti.out


def test_toplu_envanter_strict_modda_gecer(tmp_path, monkeypatch, capsys):
    _depo(tmp_path)
    for yol in (tmp_path / "sonuc").glob("*.jsonl"):
        yol.unlink()
    (tmp_path / "sonuc" / "olcum.jsonl").write_text(
        '{"adim":1,"eval_loss":0.4,"f1":0.2,"model":"synthetic","n":8}\n',
        encoding="utf-8",
    )
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "aggregate only")
    ref = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()
    monkeypatch.chdir(tmp_path)

    assert main(["--ref", ref, "--strict"]) == 0
    assert "satır_düzeyi=0" in capsys.readouterr().out
