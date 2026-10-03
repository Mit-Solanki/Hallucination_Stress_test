import os
import re
import json

def parse_docx_traps():
    with open('extracted_traps.txt', 'r', encoding='utf-8') as f:
        text = f.read()

    trap_blocks = re.split(r'\n(?=T\d{2}:)', text)[1:]
    traps = []

    field_patterns = [
        ('question', r'^Question:\s*(.*)'),
        ('false_premise', r'^False(?:\s*\(.*?\))?:\s*(.*)'),
        ('safe_behavior', r'^Safe behavior:\s*(.*)'),
        ('hallucination_example', r'^Hallucination might say:\s*(.*)'),
        ('difficulty', r'^Difficulty:\s*(.*)'),
        ('why_useful', r'^Why useful:\s*(.*)'),
        ('verify', r'^Verify:\s*(.*)')
    ]

    for block in trap_blocks:
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        header = lines[0]
        m = re.match(r'(T\d{2}):\s*(.*?)(?:\s*\((.*?)\))?$', header)
        if not m:
            print("Failed to match header:", header)
            continue
        trap_id = m.group(1)
        category = m.group(2).strip()
        trap_type = m.group(3).strip() if m.group(3) else ''

        data = {
            'id': trap_id,
            'category': category,
            'type': trap_type
        }
        curr_key = None

        for line in lines[1:]:
            matched = False
            for fkey, fpat in field_patterns:
                fm = re.match(fpat, line, re.IGNORECASE)
                if fm:
                    curr_key = fkey
                    data[curr_key] = fm.group(1).strip()
                    matched = True
                    break
            if not matched and curr_key:
                data[curr_key] += ' ' + line

        # Strip enclosing quotes around question if present
        if 'question' in data:
            q = data['question'].strip()
            if (q.startswith('"') and q.endswith('"')) or (q.startswith('“') and q.endswith('”')):
                data['question'] = q[1:-1].strip()

        traps.append(data)

    print(f"Total traps parsed: {len(traps)}")
    for t in traps:
        print(f"[{t['id']}] Cat: {t['category']} | Type: {t['type']} | Diff: {t.get('difficulty')} | Q: {t.get('question')[:50]}...")
        # Check required fields
        for req in ['id', 'question', 'category', 'type', 'difficulty', 'safe_behavior']:
            if req not in t or not t[req]:
                print(f"WARNING: missing {req} in {t['id']}")

    os.makedirs('data', exist_ok=True)
    with open('data/questions.json', 'w', encoding='utf-8') as f:
        json.dump(traps, f, indent=2, ensure_ascii=False)
    print("Saved to data/questions.json")

if __name__ == '__main__':
    parse_docx_traps()
