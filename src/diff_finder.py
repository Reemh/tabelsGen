#!/usr/bin/python
__author__ = 'Reem'

import numpy as np
import timeit

D_ROWS = 0
D_COLS = 1
D_ROWS_COLS = 2

# reads a csv file (using full file path) and returns the data table with the IDs
def get_full_table(file):
    #data = np.genfromtxt(file, dtype=None, delimiter=',', names=True)
    data = np.genfromtxt(file, dtype=np.string_, delimiter=',')
    row_ids = data[1:][:, 0]
    col_ids = data[0, :][1:]
    table = data[1:, 1:]
    return Table(row_ids, col_ids, table)


### Helper functions ###

# get the IDs available only in the first one
def get_deleted_ids(ids1, ids2):
    return list(set(ids1) - set(ids2))


# get the IDs available only in the second one
def get_added_ids(ids1, ids2):
    return list(set(ids2) - set(ids1))


def get_intersection(ids1, ids2):
    return set(ids1).intersection(ids2)


def get_union_ids(ids1, ids2):
    if len(ids1) < len(ids2):
        first = ids1
        second = ids2
    else:
        first = ids2
        second = ids1
    u = list(second)
    deleted = get_deleted_ids(first, second)
    for i in deleted:
        index1 = first.index(i)
        if index1 == 0:
            #it's deleted from the first position
            #add it at position index1
            u.insert(0, i)
        else:
            #it's somewhere in the middle, find the position of the one before
            index1 -= 1
            pre_element = first[index1]
            while pre_element not in u:
                index1 -= 1
                if index1 >= 0:
                    pre_element = first[index1]
                else:
                    print("ERROR: there's no element before that exists in the list then just add it at 0!")
                    u.insert(0, i)
                    return u
            pre_index = u.index(pre_element)
            #insert the new element after the pre_element
            u.insert(pre_index + 1, i)
            #todo if the index is not available
    return u


#helping functions from caleydo
def assign_ids(ids, idtype):
    import caleydo_server.plugin

    manager = caleydo_server.plugin.lookup('idmanager')
    return np.array(manager(ids, idtype))


#calcuate the percentage of changed cells regarding the intersection table
def calc_ch_percentage(chc, rc, cc):
    return float(chc)/(rc * cc)


def generate_diff_from_files(file1, file2):
    full_table1 = get_full_table(file1)
    full_table2 = get_full_table(file2)
    #todo use the classes
    #return generate_diff(full_table1, full_table2, None, None, 2)



#Table data structure
class Table:
    def __init__(self, rows, cols, content):
        self.row_ids = rows
        self.col_ids = cols
        self.content = content


#Diff object data structure
class Diff:
    def __init__(self, direction):
        self._direction = direction
        self.content = []
        self.structure = {}
        self.merge = {}
        self.reorder = {}

    #todo decide if the union should be here or in the diff finder
    def add_union(self, union):
        self.union = union

    def serialize(self):
        return {
            "content" : self.content,
            "structure": self.structure,
            "merge": self.merge,
            "reorder": self.reorder,
            "union": self.union
        }


#DiffFinder class
class DiffFinder:
    #todo add the operations?
    def __init__(self, t1, t2, rowtype, coltype, lod, direction):
        self._table1 = t1
        self._table2 = t2
        self._lod = lod
        self._direction = int(direction)
        self.diff = Diff(self._direction)
        self.union = {}
        self.intersection = {} #we only need this for rows when we have content changes
        self.intersection["ic_ids"] = get_intersection(self._table1.col_ids, self._table2.col_ids)
        if len(self.intersection["ic_ids"]) >= 0:
        #there's at least one common column between the tables
        #otherwise there's no need to calculate the unions
            #for now drop the if about directions because we need the unions for showing the details level and for calculating the content changes :|
            #todo reuse the these conditions when we know when we really need them
            #if self._direction == D_COLS or self._direction == D_ROWS_COLS:
            #generate the union columns
            self.union["uc_ids"] = get_union_ids(self._table1.col_ids, self._table2.col_ids)
            c_ids = assign_ids(self.union["uc_ids"], coltype)
            #use tolist() to solve the json serializable problem
            self.union["c_ids"] = c_ids.tolist()
            #if self._direction == D_ROWS or self._direction == D_ROWS_COLS:
            #generate the union rows
            self.union["ur_ids"] = get_union_ids(self._table1.row_ids, self._table2.row_ids)
            r_ids = assign_ids(self.union["ur_ids"], rowtype)
            self.union["r_ids"]= r_ids.tolist()

    def generate_diff(self, ops):
        if len(self.union) == 0:
            #todo return a special value
            #there's no diff possible
            return {}
        operations = ops.split(",")
        has_merge = "merge" in operations
        has_reorder = "reorder" in operations
        has_structure = "structure" in operations
        has_content = "content" in operations
        if self._direction == D_COLS or self._direction == D_ROWS_COLS:
            if has_structure or has_merge:
                t1 = timeit.default_timer()
                self._compare_ids("col", self._table1.col_ids, self._table2.col_ids, self.union["uc_ids"], has_merge, has_structure)
                t2 = timeit.default_timer()
            #todo check for reorder for cols here
        if self._direction == D_ROWS or self._direction == D_ROWS_COLS:
            if has_structure or has_merge:
                t3 = timeit.default_timer()
                self._compare_ids("row", self._table1.row_ids, self._table2.row_ids, self.union["ur_ids"], has_merge, has_structure)
                t4 = timeit.default_timer()
            #todo check for reorder for rows here
        #check for content change
        #todo move this to be before checking for other changes so that we can aggregate if necessary?
        if has_content:
            #todo do we need both rows and columns here anyway?
            #first calculate the rows intersections
            t5 = timeit.default_timer()
            self.intersection["ir_ids"] = get_intersection(self._table1.row_ids, self._table2.row_ids)
            #now we have both intersections for rows and columns
            t7 = timeit.default_timer()
            self._compare_values(self._table1, self._table2, self.union["ur_ids"], self.union["uc_ids"])
            t8 = timeit.default_timer()
            #todo check this here
            #ch_perc = calc_ch_percentage(len(self.diff.content), len(self.intersection["ir_ids"]), len(self.intersection["ic_ids"]))
            print("content: ", t8 - t7 , " intersection for rows: ", t7 - t5, " rows: ", t4 - t3, " cols : ", t2 - t1)
        return self.diff

    #compares two lists of ids
    #todo consider sorting
    def _compare_ids(self, e_type, ids1, ids2, u_ids, has_merge, has_structure, merge_delimiter= "+"):
        deleted = get_deleted_ids(ids1, ids2)
        deleted_log = []
        added_log = []
        #TODO use this only for merge operations :|
        merged_log = []
        split_log = []
        to_filter = []
        merge_id = 0
        for i in deleted:
            #check for a + for a split operation
            if str(i).find(merge_delimiter) == -1:
                #no delimiter found
                if i in u_ids:
                    pos = u_ids.index(i)
                    deleted_log += [{"id": i, "pos": pos}]
            else:
                #split found
                split_log += [{"id": str(i), "pos": u_ids.index(i), "split_id": merge_id, "is_added": False}]
                split_ids = str(i).split(merge_delimiter)
                to_filter += split_ids  #will be filtered in next step
                for s in split_ids:
                    split_log += [{"id": s, "pos": u_ids.index(s), "split_id": merge_id, "is_added": True}]
                merge_id += 1 #increment it
        for j in get_added_ids(ids1, ids2):
            #check for a + for merge operations!
            if str(j).find(merge_delimiter) == -1:
                #no delimiter found
                if j not in to_filter:
                    apos = u_ids.index(j)
                    added_log += [{"id": j, "pos": apos}]
                    #else:
                    #   print("this should not be logged because it's part of a split", j)
            else:
                #merge found
                merged_log += [{"id": str(j), "pos": u_ids.index(j), "merge_id": merge_id, "is_added": True}]
                merged_ids = str(j).split(merge_delimiter)
                for s in merged_ids:
                    #delete the delete operations related to those IDs
                    deleted_log = filter(lambda obj: obj['id'] != s, deleted_log)
                    merged_log += [{"id": s, "pos": u_ids.index(s), "merge_id": merge_id, "is_added": False}]
                merge_id += 1 #increment it
        #log
        if has_merge:
            self.diff.merge["merged_" + e_type + "s"] = merged_log
            self.diff.merge["split_" + e_type + "s"] = split_log
        if has_structure:
            self.diff.structure["added_" + e_type + "s"] = added_log
            self.diff.structure["deleted_" + e_type + "s"] = deleted_log

    #content changes
    def _compare_values(self, table1, table2, ru_ids, cu_ids):
        for i in self.intersection["ir_ids"]:
            r1 = table1.row_ids.index(i)
            r2 = table2.row_ids.index(i)
            for j in self.intersection["ic_ids"]:
                c1 = table1.col_ids.index(j)
                c2 = table2.col_ids.index(j)
                # cell_diff = full_table1.content[r1,c1] - full_table2.content[r2,c2]
                # doesn't work like this because it's a string
                if table1.content[r1, c1] != table2.content[r2, c2]:
                    #todo find a diff for different datatypes!
                    cell_diff = float(table1.content[r1, c1]) - float(table2.content[r2, c2])
                    rpos = ru_ids.index(i)
                    cpos = cu_ids.index(j)
                    self.diff.content += [{"row": str(i), "col": str(j), "diff_data": cell_diff, "rpos": rpos, "cpos": cpos}]
        #return diff_arrays

#todo might be an idea to find the merged things first then handle the rest separately
