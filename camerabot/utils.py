"""Utils module."""
import psutil


def kill_proc_tree(pid, including_parent=True):
    """Kill process tree.
    Kill ffmpeg process. Regular subprocess kill somehow leaves zombie.
    Really not critical but psutil works like a charm.
    """
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        child.kill()
    if including_parent:
        parent.kill()
        parent.wait(5)


def make_html_bold(text):
    return '<b>{0}</b>'.format(text)
