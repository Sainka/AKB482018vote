import pickle
import os
class PlickelTool():
    def load(self, filePath):
        if os.path.exists(filePath):
            with open(filePath, 'rb') as f:
                return pickle.load(f)
        return None, None

    def save(self, filePath, obj):
        with open(filePath, 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)