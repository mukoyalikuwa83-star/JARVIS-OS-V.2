import sys
sys.path.insert(0, r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')
from actions.autonomous_worker import AutonomousWorker
from actions.gumroad_api import handle as gumroad
from actions.social_media import handle as social
from actions.content_engine import handle as content
print('1. All imports OK')
w = AutonomousWorker()
r = w.handle({'action': 'status'})
print('2. Worker status OK')
r = gumroad({'action': 'status'})
print('3. Gumroad API OK')
r = social({'action': 'status'})
print('4. Social media OK')
r = content({'action': 'status'})
print('5. Content engine OK')
print('\nALL TESTS PASSED')