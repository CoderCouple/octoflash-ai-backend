from enum import Enum


class Tags(str, Enum):
    Health = "Health"
    Me = "Me"
    Organization = "Organization"
    Workspace = "Workspace"
    Billing = "Billing"
    Project = "Project"
    Scene = "Scene"
    Job = "Job"
    Export = "Export"
    Workflow = "Workflow"
    Source = "Source"
    Target = "Target"
    Voice = "Voice"
    Playground = "Playground"
    Credential = "Credential"
    Contact = "Contact"
