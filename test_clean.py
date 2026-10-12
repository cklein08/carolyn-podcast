from generate_podcast import clean_for_speech
import re

test = r"""# Heineken EA Brief

## Overview & Strategy

**Freddy.Connect** is a platform that connects `creators` with [brands](https://example.com).

### Key Priorities
1. **Brand consistency** across all channels
2. *Speed to market* — reduce from 6 weeks to 2 days
3. Data-driven creative decisions

> This is a blockquote about something important.

- First bullet point
- Second point with a [link](https://heineken.com)
- Third with **bold text**

---

## ROI Analysis
| Metric | Before | After |
|--------|--------|-------|
| Time   | 6 weeks| 2 days|

The ROI is EUR 4M ARR over 4 years. E.g. 40% cost reduction.
See #GenStudio #Firefly for details.

![workflow diagram](https://example.com/diagram.png)

~~Old process~~ vs new process.
"""

cleaned = clean_for_speech(test)
print("=== CLEANED OUTPUT ===")
print(cleaned)
print("=== END ===")
print()

# Check no markdown artifacts remain
issues = []
for pattern, name in [
    (r'\*\*', 'bold'),
    (r'`', 'backtick'),
    (r'^#{1,6}\s', 'header'),
    (r'^\s*\|.*\|', 'table'),
    (r'^\s*>\s', 'blockquote'),
    (r'^\s*[-+]\s', 'list-marker'),
    (r'^\s*\d+\.\s', 'numbered-list'),
    (r'https?://', 'URL'),
    (r'(?<!\w)\|(?!\w)', 'pipe'),
]:
    if re.search(pattern, cleaned, re.MULTILINE):
        issues.append(name)

if issues:
    print(f"WARNING: Still contains: {issues}")
else:
    print("SUCCESS: No markdown artifacts remaining!")
