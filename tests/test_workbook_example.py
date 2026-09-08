"""Synthetic ZIP fixture changes test the checker, not a model or calculation engine."""
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import pytest
from wikiskill.product import normalize_tasks

EXAMPLE=Path(__file__).resolve().parents[1]/'examples/workbook-delivery'
spec=importlib.util.spec_from_file_location('workbook_score',EXAMPLE/'score.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def fixture_output(task,destination, *, caches=True, formula=True, tamper=False):
    from openpyxl import load_workbook
    source=Path(task['files'][0]);book=load_workbook(source);sheet=book['Order'];end=task['input']['total_row']
    expected={f'D{r}':sheet[f'B{r}'].value*sheet[f'C{r}'].value for r in range(4,end)}
    expected[f'D{end}']=sum(expected.values());book.close()
    with ZipFile(source) as incoming,ZipFile(destination,'w') as outgoing:
        for item in incoming.infolist():
            data=incoming.read(item.filename)
            if item.filename=='xl/worksheets/sheet1.xml':
                root=ET.fromstring(data)
                for row in root.findall(f'.//{{{NS}}}row'):
                    r=int(row.attrib['r']);coord=f'D{r}'
                    if coord not in expected:continue
                    cell=next((c for c in row if c.attrib.get('r')==coord),None)
                    if cell is None:cell=ET.SubElement(row,f'{{{NS}}}c',{'r':coord})
                    cell.attrib.pop('t',None)
                    for child in list(cell):cell.remove(child)
                    if formula:ET.SubElement(cell,f'{{{NS}}}f').text=f'B{r}*C{r}' if r<end else f'SUM(D4:D{end-1})'
                    if caches:ET.SubElement(cell,f'{{{NS}}}v').text=str(expected[coord])
                if tamper:
                    cell=root.find(f'.//{{{NS}}}c[@r="B4"]/{{{NS}}}v');cell.text='999'
                data=ET.tostring(root)
            outgoing.writestr(item,data)


@pytest.mark.parametrize('case',range(4))
def test_example_checker_all_inputs_and_corruptions(tmp_path,case):
    task=normalize_tasks(EXAMPLE/'tasks.json')[case]
    out=tmp_path/'output.xlsx';payload={'task':task,'output':{'path':str(out)}}
    fixture_output(task,out);assert module.score(payload)['score']==1
    fixture_output(task,out,caches=False);assert module.score(payload)['score']==pytest.approx(2/3)
    fixture_output(task,out,formula=False);assert module.score(payload)['score']==pytest.approx(2/3)
    fixture_output(task,out,tamper=True);assert module.score(payload)['score']==pytest.approx(2/3)
    out.write_text('not a workbook');assert module.score(payload)['score']==0
