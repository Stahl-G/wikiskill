from pathlib import Path
from wikiskill.cli import main

def test_study_prepare_has_bounded_defaults_and_no_run(tmp_path,monkeypatch):
    from wikiskill.spreadsheet import study
    calls=[]
    def prepare(root,**kw):calls.append((root,kw));return {'phase':'prepared'}
    monkeypatch.setattr(study,'prepare',prepare)
    assert main(['spreadsheet-study','prepare',str(tmp_path/'run'),'--data',str(tmp_path/'data'),'--split-dir',str(tmp_path/'split'),'--libreoffice-app',str(tmp_path/'office.app')])==0
    root,kw=calls[0]
    assert root==tmp_path/'run' and kw['train_limit']==8 and kw['val_limit']==4
    assert kw['workers']==2 and kw['model']=='gpt-5.6-luna' and kw['effort']=='high'
