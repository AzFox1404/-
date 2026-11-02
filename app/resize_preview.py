"""Window sizing uses Windows' normal compositor; no native subclass or capture."""
def install(window):
    # The former WM_SIZING snapshot hook interfered with Tk child repainting.
    # Internal splitters use a short-lived glass cover instead (glass_resize).
    return
