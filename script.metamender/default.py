"""MetaMender script entry point: the add-on's own launch, its settings
buttons and RunScript actions (resources/lib/service/entry.py)."""
import sys

from resources.lib.service.entry import main

if __name__ == "__main__":
    main(sys.argv[1:])
