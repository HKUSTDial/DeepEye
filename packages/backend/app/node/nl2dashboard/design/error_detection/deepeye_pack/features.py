"""
此文件定义了两个类Type和Feature：
Type类主要用于根据数据类型进行分类，最终分为categorical，numerical和temporal三类，在view.py, table.py, table_l.py
文件中进行算法实现时，根据数据Type类型的不同，进行的操作也有所差异。
Features类用于存储数据的一些特征信息，如名称(name)，类型(type)，数据来源(origin)，最小值(min)，最大值(max)等。
"""

class Type(object):
    none = 0
    categorical = 1
    numerical = 2
    temporal = 3

    @staticmethod
    def getType(s):
        """
        Input the table_info.

        Args:
            s(str): data type, including varchar, year, int, float, etc.

        Returns:
            data type expressed by number 0(none), 1(categorical), 2(numerical), 3(temporal)
            
        """
        if len(s) >= 7 and s[0:7] == 'varchar':
            return Type.categorical
        elif len(s) >= 4 and s[0:4] == 'year':
            return Type.temporal
        elif len(s) >= 4 and s[0:4] == 'char':
            return Type.categorical
        elif len(s) >= 3 and s[0:3] == 'int':
            return Type.numerical
        elif s == 'int' or s == 'double' or s == 'float':
            return Type.numerical
        elif s == 'date' or s == 'datetime' or s == 'year':
            return Type.temporal
        else:
            return Type.none


class Features(object):
    """
    Store the attributes of a column in the table, such as min, max, etc.
    Attributes:
        name(str): the name of the corresponding column.
        type(Type): the type of the corresponding column.
        origin(list): which column the data from.
        min(float): min value of the column.
        minmin(float): used in table.py
        max(float): max value of the column.
    """
    def __init__(self, name, type, origin):
        self.name = name
        self.type = type
        self.origin = origin  # origin data from db
        self.min = self.minmin = self.max = self.distinct = self.ratio = self.bin_num = 0
        self.interval = ''
        self.distinct_values = []
        self.interval_bins = []
