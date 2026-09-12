import json
from PIL import Image
from backend.app.config import Settings
from backend.app.ingestion import digest, image_text
from backend.app.pdf_text import broken_text


def test_broken_font_detection():
    assert broken_text('\x01\x02\x03'*100)
    assert not broken_text('A normal course paragraph contains useful readable text about several important concepts.')


def test_transcription_provenance_and_hash(tmp_path):
    image=tmp_path/'note.png'
    Image.new('RGB',(20,20),'white').save(image)
    data={'source_sha256':digest(image),'reviewed':True,'reviewer':'test fixture author','method':'synthetic_fixture','quality':'MEDIUM','text':'Arrays store indexed elements.'}
    sidecar=image.with_suffix('.png.transcript.json')
    sidecar.write_text(json.dumps(data))
    assert image_text(image,Settings())==('Arrays store indexed elements.','MEDIUM','synthetic_fixture')
    data['source_sha256']='wrong'
    sidecar.write_text(json.dumps(data))
    import pytest
    with pytest.raises(ValueError,match='hash'):
        image_text(image,Settings())
