STATUSES = ("todo", "in_progress", "done")
PRIORITIES = ("low", "medium", "high")
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000


class ValidationError(Exception):
    def __init__(self, details):
        super().__init__("Validation failed")
        self.details = details


def validate_task(data, partial=False):
    """Return a cleaned dict containing only allowed fields, or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "Expected a JSON object."})

    errors, cleaned = {}, {}

    if "title" in data or not partial:
        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            errors["title"] = "Title is required."
        elif len(title.strip()) > MAX_TITLE_LENGTH:
            errors["title"] = f"Title must be at most {MAX_TITLE_LENGTH} characters."
        else:
            cleaned["title"] = title.strip()

    if "description" in data:
        description = data["description"]
        if description is not None and not isinstance(description, str):
            errors["description"] = "Description must be a string."
        elif description and len(description) > MAX_DESCRIPTION_LENGTH:
            errors["description"] = f"Description must be at most {MAX_DESCRIPTION_LENGTH} characters."
        else:
            cleaned["description"] = description.strip() if description else None

    for field, allowed in (("status", STATUSES), ("priority", PRIORITIES)):
        if field in data:
            if data[field] not in allowed:
                errors[field] = f"Must be one of: {', '.join(allowed)}."
            else:
                cleaned[field] = data[field]

    if errors:
        raise ValidationError(errors)
    if partial and not cleaned:
        raise ValidationError({"body": "No updatable fields supplied."})
    return cleaned
