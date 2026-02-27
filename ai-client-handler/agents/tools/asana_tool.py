import asana
from asana.rest import ApiException
from agents import function_tool
from config import settings

# Asana API client — reused across tool calls
_configuration = asana.Configuration()
_configuration.access_token = settings.ASANA_ACCESS_TOKEN


@function_tool
async def get_project_status(project_name: str) -> str:
    """Get the current status and open tasks of a client project in Asana.

    Search by project name within the configured workspace and return a
    human-readable summary of open tasks and their assignees.
    """
    with asana.ApiClient(_configuration) as api_client:
        projects_api = asana.ProjectsApi(api_client)
        tasks_api = asana.TasksApi(api_client)

        try:
            # Find project by name in workspace
            projects = projects_api.get_projects(
                workspace=settings.ASANA_WORKSPACE_ID,
                opt_fields=["name", "gid", "current_status_update"],
            )

            matched = None
            for project in projects:
                if project_name.lower() in project["name"].lower():
                    matched = project
                    break

            if not matched:
                return f"No project found matching '{project_name}' in your workspace."

            # Fetch open tasks for the matched project
            tasks = tasks_api.get_tasks_for_project(
                matched["gid"],
                opt_fields=["name", "assignee.name", "due_on", "completed"],
            )

            open_tasks = [t for t in tasks if not t.get("completed")]

            if not open_tasks:
                return f"Project '{matched['name']}' has no open tasks."

            lines = [f"Project: {matched['name']}", f"Open tasks ({len(open_tasks)}):"]
            for task in open_tasks[:10]:  # cap at 10 to keep reply concise
                assignee = task.get("assignee", {})
                assignee_name = assignee.get("name", "Unassigned") if assignee else "Unassigned"
                due = task.get("due_on") or "no due date"
                lines.append(f"  • {task['name']} — {assignee_name} (due: {due})")

            if len(open_tasks) > 10:
                lines.append(f"  ... and {len(open_tasks) - 10} more tasks")

            return "\n".join(lines)

        except ApiException as e:
            return f"Asana API error: {e.status} {e.reason}"


@function_tool
async def create_client_task(title: str, description: str, project_id: str) -> str:
    """Create a new task in Asana based on a client request.

    Use this when a client asks you to log a bug, feature request, or any
    action item. project_id must be the Asana project GID (numeric string).
    Returns a confirmation message with the new task URL.
    """
    with asana.ApiClient(_configuration) as api_client:
        tasks_api = asana.TasksApi(api_client)

        try:
            task_body = {
                "data": {
                    "name": title,
                    "notes": description,
                    "projects": [project_id],
                    "workspace": settings.ASANA_WORKSPACE_ID,
                }
            }
            created = tasks_api.create_task(task_body, opt_fields=["name", "permalink_url"])
            url = created.get("permalink_url", "")
            return f"Task created: '{created['name']}'\n{url}"

        except ApiException as e:
            return f"Failed to create task: {e.status} {e.reason}"
