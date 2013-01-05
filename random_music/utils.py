
import os

def which(filename):
    """
    Equivalent of unix which command - return full path to a filename if it
    exists in the current environment, otherwise return None.
    
    :param filename: filename we are checking 
    :type filename: str
    """
    for path in os.environ["PATH"].split(os.pathsep):
        potential_path = os.path.join(path, filename)
        if os.path.exists(potential_path):
            break
        else:
            potential_path = None
    return potential_path
