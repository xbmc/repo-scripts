import migration
import service
from resources.lib.utils import housekeeper

if __name__ == "__main__":

    migration.migrate()
    housekeeper.cleanup_outdated_timers()
    service.run()
