import re
content = open('main.py', 'r', encoding='utf-8').read()
start = content.find('TOOL_DECLARATIONS = [')
# Find the closing ] of TOOL_DECLARATIONS
bracket_count = 0
end = start
for i, ch in enumerate(content[start:], start):
    if ch == '[':
        bracket_count += 1
    elif ch == ']':
        bracket_count -= 1
        if bracket_count == 0:
            end = i + 1
            break
block = content[start:end]
tools = re.findall(r'"name":\s*"(\w+)"', block)
print(f"Tool declarations: {len(tools)}")
for i, t in enumerate(tools, 1):
    print(f"  {i}. {t}")
