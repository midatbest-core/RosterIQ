"""Import all models so SQLAlchemy and Alembic see complete metadata."""

from app.modules.auth.models import User  # noqa: F401
from app.modules.auth.notification_models import Notification  # noqa: F401
from app.modules.operations.models import (  # noqa: F401
    Brand,
    BrandProcess,
    Holiday,
    HolidayCalendar,
    PrimaryAssignment,
    Process,
)
from app.modules.operations.pattern_models import (  # noqa: F401
    OperatingOverride,
    OperatingPattern,
)
from app.modules.operations.request_models import BrandChangeRequest  # noqa: F401
from app.modules.roster.models import (  # noqa: F401
    AllocationType,
    ConflictSeverity,
    ConflictType,
    EmployeeShift,
    Roster,
    RosterAllocation,
    RosterConflict,
    RosterStatus,
)
from app.modules.workforce.availability_models import (  # noqa: F401
    AbsenceReasonType,
    EmployeePreference,
    EmployeeUnavailability,
)
from app.modules.workforce.request_models import EmployeeAvailabilityRequest  # noqa: F401
from app.modules.workforce.models import (  # noqa: F401
    Employee,
    EmployeeProcessSkill,
    Pod,
    PodLead,
)
