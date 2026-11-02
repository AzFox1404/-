"""Wait for asynchronous PDF readiness in UI integration tests."""
import time

def wait_pdf(root,viewer,timeout=10):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  root.update()
  if viewer.pages and viewer.images:return
  time.sleep(.01)
 raise AssertionError('PDF renderer did not become ready: '+viewer.selection.message.get())
