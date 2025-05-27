from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from typing import List, Optional, Union

# --- Jira Issue Models ---
class JiraIssueItem(BaseModel):
    key: str = Field(..., description="The unique key of the Jira issue (e.g., PSIMDESASW-11543).")
    summary: str = Field(..., description="A brief summary or title of the issue.")
    status: str = Field(..., description="The current status of the issue (e.g., Backlog, In Progress).")
    assignee: Optional[str] = Field(None, description="The name of the person assigned to the issue. Can be null or 'Unassigned'.")

class JiraIssueListOutput(BaseModel):
    issues: List[JiraIssueItem] = Field(..., description="A list of Jira issues.")
    message: Optional[str] = Field(None, description="An optional message, e.g., 'No issues found matching your criteria.'")

class JiraWorklogEntry(BaseModel):
    author: str = Field(..., description="The display name of the user who logged the work.")
    time_spent_seconds: int = Field(..., description="Time spent in seconds.")
    time_spent_friendly: str = Field(..., description="Time spent in a human-readable format (e.g., '2h 30m').")
    started: str = Field(..., description="The date and time the worklog was started (ISO format or friendly).")
    comment: Optional[str] = Field(None, description="Optional comment associated with the worklog.")

class JiraIssueWorklogReport(BaseModel):
    issue_key: str = Field(..., description="The key of the issue for which the worklog is reported.")
    total_time_spent_seconds: int = Field(..., description="Total time spent on the issue in seconds.")
    total_time_spent_friendly: str = Field(..., description="Total time spent in a human-readable format.")
    worklogs_by_user: List[JiraWorklogEntry] = Field(..., description="A list of worklog entries, ideally grouped or sortable by user.")
    summary_message: Optional[str] = Field(None, description="A summary message, e.g., detailing total hours per user if aggregated.")


# --- Confluence Page Models ---
class ConfluencePageItem(BaseModel):
    title: str = Field(..., description="The title of the Confluence page.")
    space: Optional[str] = Field(None, description="The name of the Confluence space the page belongs to.")
    author: Optional[str] = Field(None, description="The original creator of the page.")
    last_modified: Optional[str] = Field(None, description="The date of the last modification.")
    description: Optional[str] = Field(None, description="A brief description or excerpt of the page content.")
    url: Optional[HttpUrl] = Field(None, description="The full URL to view the Confluence page.")

class ConfluencePageListOutput(BaseModel):
    pages: List[ConfluencePageItem] = Field(..., description="A list of Confluence pages.")
    message: Optional[str] = Field(None, description="An optional message, e.g., 'No pages found matching your criteria.'")


# --- Jira User Models ---
class JiraUserItem(BaseModel):
    display_name: str = Field(..., alias="name", description="The full display name of the Jira user.")
    email: Optional[str] = Field(None, description="The email address of the user.")
    account_id: str = Field(..., description="The unique account ID of the Jira user.")
    active: bool = Field(..., description="Indicates whether the user account is active.")

    model_config = ConfigDict(validate_by_name=True)

class JiraUserListOutput(BaseModel):
    users: List[JiraUserItem] = Field(..., description="A list of Jira users found.")
    exact_match_found: Optional[bool] = Field(False, description="Indicates if an exact match was found among the results (primarily for validate_jira_user).")
    message: Optional[str] = Field(None, description="An optional message, e.g., 'No users found' or 'Multiple users found, please specify.'")

    model_config = ConfigDict(validate_by_name=True)


# --- Jira Issue Transition Models ---
class JiraIssueTransitionField(BaseModel):
    name: str = Field(..., description="The name of the required field.")
    # Add more details if get_issue_transitions provides schema for these fields
    # type: str = Field(..., description="The type of the field (e.g., string, user, date).")
    # required: bool = Field(..., description="Whether the field is mandatory for the transition.")

class JiraIssueTransitionItem(BaseModel):
    id: str = Field(..., description="The unique ID of the transition.")
    name: str = Field(..., description="The human-readable name of the transition (e.g., 'Start Progress').")
    target_status: str = Field(..., alias="to_status_name", description="The name of the status the issue will be in after this transition.")
    has_screen: bool = Field(False, description="Indicates if the transition has an associated screen for additional input.")
    required_fields: List[JiraIssueTransitionField] = Field([], description="A list of fields that are required for this transition, if any.")

    model_config = ConfigDict(validate_by_name=True)

class JiraIssueTransitionsOutput(BaseModel):
    issue_key: str = Field(..., description="The key of the issue for which transitions are listed.")
    current_status: str = Field(..., description="The current status of the Jira issue.")
    transitions: List[JiraIssueTransitionItem] = Field(..., description="A list of available transitions for the issue.")
    message: Optional[str] = Field(None, description="An optional message, e.g., 'No transitions available.'")

# --- Sprint Information Models ---
class SprintIssueSummary(BaseModel):
    key: str
    summary: str
    status: str
    assignee: Optional[str]
    story_points: Optional[float] = Field(None, description="Story points estimated for the issue, if applicable.")

class SprintDetails(BaseModel):
    id: int
    name: str
    goal: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    state: str # e.g., active, future, closed

class ActiveSprintIssuesOutput(BaseModel):
    sprint: Optional[SprintDetails] = Field(None, description="Details of the active sprint, if one is found.")
    issues: List[SprintIssueSummary] = Field(..., description="List of issues in the active sprint.")
    project_key: Optional[str] = Field(None, description="Project key if the query was project-specific.")
    message: Optional[str] = Field(None, description="Optional message, e.g., 'No active sprint found for project X'.")

class UserSprintWorkOutput(BaseModel):
    sprint: Optional[SprintDetails] = Field(None, description="Details of the active sprint.")
    user_issues: List[SprintIssueSummary] = Field(..., description="List of issues assigned to the current user in the active sprint.")
    total_issues: int
    total_story_points: Optional[float] = Field(None)
    project_key: Optional[str] = Field(None, description="Project key if the query was project-specific.")
    message: Optional[str] = Field(None, description="Optional message.")

class SprintProgressOutput(BaseModel):
    sprint: SprintDetails
    total_issues: int
    issues_completed: int
    issues_in_progress: int
    issues_to_do: int
    percentage_completed_issues: float = Field(..., description="Based on issue count.")
    total_story_points: Optional[float] = Field(None)
    story_points_completed: Optional[float] = Field(None)
    percentage_completed_story_points: Optional[float] = Field(None, description="Based on story points, if available.")
    days_remaining: Optional[str] = Field(None) # Can be string like "3 days" or an int
    issues_by_status: dict[str, int] = Field(..., description="Count of issues per status name.")
    story_points_by_status: Optional[dict[str, float]] = Field(None, description="Sum of story points per status name.")
    project_key: Optional[str] = Field(None, description="Project key if the query was project-specific.")

# --- General Purpose Models ---
class ConfirmationOutput(BaseModel):
    action_description: str = Field(..., description="A description of the action performed or to be performed.")
    status: str = Field(..., description="Status of the action (e.g., 'Success', 'Pending Confirmation', 'Failed').")
    details: Optional[str] = Field(None, description="Additional details about the action or its result.")

class ErrorOutput(BaseModel):
    error_message: str = Field(..., description="A description of the error that occurred.")
    suggestion: Optional[str] = Field(None, description="A suggestion for how the user might proceed or fix the issue.")

# Example of a more complex output if a tool returns a creation result
class CreatedConfluencePage(BaseModel):
    id: str
    title: str
    space_key: str
    url: HttpUrl
    version: int 