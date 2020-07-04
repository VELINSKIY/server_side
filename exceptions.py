"""All project related Exception Definitions
"""

class ValidationException(Exception):
    """Generic Exception rasied for all validation activities
    """

class EntityNotFoundException(ValidationException):
    """Generic exception thrown at the event when needed entity is not found
    """
    def __init__(self, entity_type: str, entity_id: str, txt=''):
        super(EntityNotFoundException, self).__init__(
            f"{entity_type} ({entity_id}) not found {txt}"
        )
        
        # Super() returns an object (temporary object of the superclass) 
        # that allows us to access methods of the base class.