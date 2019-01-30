from django.db.models import Q
from django.conf import settings

from timepiece import utils

from timepiece.manager.models import Project
from timepiece.entries.models import Entry


def quick_clock_in(request):
    user = request.user
    work_projects = []
    leave_projects = []

    if user.is_active:
        # Get all projects this user has clocked in to.
        entries = Entry.objects.filter(user=user)
        project_ids = list(entries.values_list('project', flat=True))

        # Narrow to projects which can still be clocked in to.
        pq = Q(id__in=project_ids)
        valid_projects = Project.objects.filter(pq)
        valid_ids = list(valid_projects.values_list('id', flat=True))

        # Display the 10 projects this user most recently clocked into.
        work_ids = []
        for i in project_ids:
            if len(work_ids) > 10:
                break
            if i in valid_ids and i not in work_ids:
                work_ids.append(i)
        work_projects = [valid_projects.get(pk=i) for i in work_ids]

    return {
        'work_projects': work_projects,
    }

