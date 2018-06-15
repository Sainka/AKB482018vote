import os
from .utf8logger import INFO,PRINT
class FileTool():
    def split(self, fromfile, todir, chunkLineSize):
        if not os.path.exists(todir):  # check whether todir exists or not
            os.mkdir(todir)
        else:
            for fname in os.listdir(todir):
                os.remove(os.path.join(todir, fname))
        partnum = 0
        with open(fromfile, 'rb') as input:
            while True:
                chunk = input.readlines(chunkLineSize)
                if not chunk:  break
                filename = os.path.join(todir, ('part%04d' % partnum))
                with open(filename, 'wb') as out:
                    out.writelines(chunk)
                partnum += 1
        return partnum

    def merge(self, fromdir, tofile):
        if os.path.exists(fromdir):
            totolid = 0
            with open(tofile, 'wb') as output:
                flist = list(filter(lambda x: 'log' in x and os.path.basename(tofile) not in x, os.listdir(fromdir)))
                INFO(flist)
                for sname in flist:
                    fname = os.path.join(fromdir, sname)
                    with open(fname, 'rb') as input:
                        while True:
                            chunk = input.readlines(1024)
                            if not chunk:  break
                            for line in chunk:
                                if not line: continue
                                s = '%07d, %s' % (totolid, line.decode('utf-8'))
                                PRINT(s, end='')
                                output.write(s.encode(encoding='utf-8'))
                                totolid += 1
