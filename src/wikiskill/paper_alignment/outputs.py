"""Normalize the paper Maintainer's documented direct-JSON return contract."""
from wikiskill.skill_proposer import _extract_answer
from .contracts import wiki_update


def maintainer_submission(final_text, wiki):
    """Validate exactly as finish would; no missing-output fallback or score."""
    value=_extract_answer(final_text)
    normalized,_=wiki_update(value,wiki)
    return {'proposal':normalized,'read_trace_ids':[]}
