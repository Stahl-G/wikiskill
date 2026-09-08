"""Example external scorer: JSON stdin, JSON stdout; no model calls."""
import json
import sys

request = json.load(sys.stdin)
actual = request['output']['text'].strip()
expected = request['task']['reference']
matched = actual == expected
print(json.dumps({'score': float(matched), 'success': matched,
                  'feedback': 'Correct normalized label.' if matched else
                  'The output must be lowercase, trimmed, and contain single spaces between words.'}))
