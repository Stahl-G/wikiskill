from pathlib import Path
import pytest
from wikiskill import product as p
from wikiskill.cli import main
import json
from wikiskill.product_install import install, restore
from test_product import tasks, finish_tasks, learn_propose


def completed(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1))
    finish_tasks(root,tmp_path,0);finish_tasks(root,tmp_path,0)
    learn_propose(root,tmp_path,body='# Learned');finish_tasks(root,tmp_path,1)
    return root


def test_replace_restore_preserves_support_and_user_edits(tmp_path):
    root=completed(tmp_path);dest=tmp_path/'user-skill';dest.mkdir()
    (dest/'SKILL.md').write_text('# Original');(dest/'helper.py').write_text('keep')
    with pytest.raises(ValueError,match='--replace'):install(root,dest)
    result=install(root,dest,replace=True)
    assert (dest/'SKILL.md').read_text()=='# Learned'
    assert not install(root,dest,replace=True)['changed']
    (dest/'SKILL.md').write_text('# User changed')
    with pytest.raises(ValueError,match='changed since'):restore(dest,result['backup_id'])
    (dest/'SKILL.md').write_text('# Learned')
    restore(dest,result['backup_id'])
    assert (dest/'SKILL.md').read_text()=='# Original'
    assert not restore(dest,result['backup_id'])['changed']
    assert (dest/'helper.py').read_text()=='keep'
    assert p.status(root)['best_score']==1


def test_new_install_undo_and_tamper_checks(tmp_path):
    root=completed(tmp_path);dest=tmp_path/'new'
    result=install(root,dest);restore(dest,result['backup_id'])
    assert not (dest/'SKILL.md').exists()
    (dest/'SKILL.md').write_text('original');result=install(root,dest,replace=True)
    (Path(result['backup'])/'previous.md').write_text('tamper')
    with pytest.raises(ValueError,match='Backup content'):restore(dest,result['backup_id'])
    with pytest.raises(ValueError,match='backup ID'):restore(dest,'../escape')
    with pytest.raises(ValueError,match='outside'):install(root,root/'skill')


def test_unfinished_and_no_retained_skill_cannot_install(tmp_path):
    root=tmp_path/'flow';p.start(root,tasks=tasks(tmp_path,n=1))
    with pytest.raises(ValueError,match='Finish'):install(root,tmp_path/'target')
    finish_tasks(root,tmp_path,1);finish_tasks(root,tmp_path,1);learn_propose(root,tmp_path,no_action=True)
    with pytest.raises(ValueError,match='No retained'):install(root,tmp_path/'target')


def test_install_restore_cli(tmp_path,capsys):
    root=completed(tmp_path);destination=tmp_path/'cli-install'
    assert main(['install',str(root),str(destination)])==0
    result=json.loads(capsys.readouterr().out)
    assert main(['restore',str(destination),'--backup',result['backup_id']])==0
    assert json.loads(capsys.readouterr().out)['restored']
    assert not (destination/'SKILL.md').exists()
