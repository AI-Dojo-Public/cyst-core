from tools.scenario_creat.action_mapper.solver import Solver
from tools.scenario_creat.action_mapper.constraints import Tables, ActionToken, TokensAccounting



path_host = 5
path_service = 5
path_action = 5
path_token = 5
Path_AOUT = [[1, 0, 0, 0, 0],
             [1, 1, 0, 0, 0],
             [0, 1, 1, 0, 0],
             [0, 0, 1, 1, 0],
             [0, 0, 0, 1, 1]]

Path_AIN = [[1, 0, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [0, 1, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 0, 1, 0]]

Path_AS = [[1, 0, 0, 0, 0],
           [0, 1, 0, 0, 0],
           [0, 0, 1, 0, 0],
           [0, 0, 0, 1, 0],
           [0, 0, 0, 0, 1]]

Path_HH = [[0, 1, 0, 0, 0],
           [0, 0, 1, 0, 0],
           [0, 0, 0, 1, 0],
           [0, 0, 0, 0, 1],
           [0, 0, 0, 0, 0]]

Path_AT = [ActionToken.NONE]

# simple diamond

Diamond_host = 6
Diamond_service = 6
Diamond_action = 6
Diamond_token = 6
Diamond_AOUT = [[0, 0, 0, 0, 0, 1],
                [1, 1, 0, 0, 0, 0],
                [0, 1, 1, 0, 0, 0],
                [0, 1, 0, 1, 0, 0],
                [0, 0, 1, 1, 1, 0],
                [0, 0, 0, 0, 1, 0]]

Diamond_AIN = [[0, 0, 0, 0, 0, 1],
               [1, 0, 0, 0, 0, 0],
               [0, 1, 0, 0, 0, 0],
               [0, 1, 0, 0, 0, 0],
               [0, 0, 1, 1, 0, 0],
               [0, 0, 0, 0, 1, 0]]

Diamond_AS = [[1, 0, 0, 0, 0, 0],
              [0, 1, 0, 0, 0, 0],
              [0, 0, 1, 0, 0, 0],
              [0, 0, 0, 1, 0, 0],
              [0, 0, 0, 0, 1, 0],
              [0, 0, 0, 0, 0, 1]]

Diamond_HH = [[0, 1, 0, 0, 0, 0],
              [0, 0, 1, 1, 0, 0],
              [0, 0, 0, 0, 1, 0],
              [0, 0, 0, 0, 1, 0],
              [0, 0, 0, 0, 0, 1],
              [0, 0, 0, 0, 0, 0]]

Diamond_AT = [ActionToken.NONE]



# Cross diamond
CRD_tokens = 6
CRD_actions = 7
CRD_services = 7
CRD_hosts = 7

CRD_HH = [[0, 1, 1, 0, 0, 0, 0],
          [0, 0, 0, 1, 0, 0, 0],
          [0, 0, 0, 1, 1, 0, 0],
          [0, 0, 0, 0, 0, 1, 0],
          [0, 0, 0, 0, 0, 1, 0],
          [0, 0, 0, 0, 0, 0, 1],
          [0, 0, 0, 0, 0, 0, 0]]

CRD_AS = [[0 for i in range(0,7)] for j in range(0,7)]
for i in range(0,7):
    CRD_AS[i][i] = 1
# diagonal

CRD_AT = [ActionToken.NONE]


# double cross diamond
DCD_tokens = 6
DCD_actions = 7
DCD_services = 7
DCD_hosts = 6

DCD_HH = [[0, 1, 1, 0, 0, 0],
          [0, 0, 0, 1, 1, 0],
          [0, 0, 0, 1, 1, 0],
          [0, 0, 0, 0, 0, 1],
          [0, 0, 0, 0, 0, 1],
          [0, 0, 0, 0, 0, 0]]

DCD_AS = [[0 for i in range(0,7)] for j in range(0,7)]
for i in range(0,7):
    DCD_AS[i][i] = 1

DCD_AT = [ActionToken.NONE]


# alternative paths
AP_tokens = 6
AP_actions = 8
AP_services = 8
AP_hosts = 8
AP_HH = [[0, 1, 0, 1, 1, 0, 0, 0],
         [0, 0, 1, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 1, 0, 0],
         [0, 0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 0, 1],
         [0, 0, 0, 0, 0, 0, 0, 0]]

AP2_HH = [[0, 1, 0, 1, 1, 0, 0, 0],
         [0, 0, 1, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 1, 1, 0],
         [0, 0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 0, 1],
         [0, 0, 0, 0, 0, 0, 0, 0]]


AP_AS = [[0 for i in range(0,8)] for j in range(0,8)]
for i in range(0,8):
    AP_AS[i][i] = 1

AP_AT = [ActionToken.NONE]

# speartip

ST_tokens = 6
ST_actions = 7
ST_services = 7
ST_hosts = 7

ST_HH = [[0, 1, 0, 0, 0, 0, 0],
         [0, 0, 1, 1, 1, 0, 0],
         [0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 1],
         [0, 0, 0, 0, 0, 0, 0]]

ST_AS = [[0 for i in range(0,7)] for j in range(0,7)]
for i in range(0,7):
    ST_AS[i][i] = 1

ST_AT = [ActionToken.NONE]

#cluster no repetition test
clus_hosts = 6
clus_services = 6
clus_actions = 6
clus_tokens =6

clus_HH = [[0, 1, 1, 0, 0, 0],
           [0, 0, 0, 1, 0, 0],
           [0, 0, 0, 0, 1, 0],
           [0, 0, 0, 0, 0, 1],
           [0, 0, 0, 0, 0, 1],
           [0, 0, 0, 0, 0, 0]]
clus_AS = [[0 for i in range(0,6)] for j in range(0,6)]
for i in range(0,6):
    clus_AS[i][i] = 1
clus_AT = [ActionToken.NONE]
clus_CT = [[0,5], [], [1,2,3], [4]]

#trident

trident_hosts = 5
trident_services = 5
trident_actions = 5
trident_tokens = 6

trident_HH = [[0,1,0,0,0],
              [0,0,1,1,1],
              [0,0,0,0,0],
              [0,0,0,0,0],
              [0,0,0,0,0]]

trident_AS = [[0 for i in range(0,5)] for j in range(0,5)]
for i in range(0,5):
    trident_AS[i][i] = 1

trident_AT = [ActionToken.NONE]
trident_dummies = [2, 3]

#long trident

lt_hosts = 7
lt_services = 6
lt_actions = 6
lt_tokens = 6

lt_HH = [[0,1,0,0,0,0,0],
         [0,0,1,1,0,0,1],
         [0,0,0,0,0,1,0],
         [0,0,0,0,1,0,0],
         [0,0,0,0,0,0,0],
         [0,0,0,0,0,0,0],
         [0,0,0,0,0,0,0]]

lt_AS = [[0 for i in range(0,6)] for j in range(0,6)]
for i in range(0,6):
    lt_AS[i][i] = 1

lt_AT = [ActionToken.NONE]
lt_dummies = [2, 3, 4, 5]






def main():
    keyword = "long-trident"

    if keyword == "path":

        tables = Tables(path_host, path_service, path_action, path_token)
        tables.hhm = Path_HH
        tables.asm = Path_AS
        tables.atm = Path_AT
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.DATA, ActionToken.DATA)
        accounting.add(1, ActionToken.NONE, ActionToken.NONE)
        accounting.add(2, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(3, ActionToken.SESSION, ActionToken.AUTH)
        accounting.add(4, ActionToken.AUTH , ActionToken.DATA)


        solver1 = Solver(tables, accounting)
        res = solver1.solve_all(4,4,4, [ActionToken.DATA])
        for i, sol in enumerate(res):
            print(i, solver1.show(sol))

    if keyword == "diamond":
        tables2 = Tables(Diamond_host, Diamond_service, Diamond_action, Diamond_token)
        tables2.hhm = Diamond_HH
        tables2.asm = Diamond_AS
        tables2.atm = Diamond_AT
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.DATA, ActionToken.DATA)
        accounting.add(1, ActionToken.NONE, ActionToken.NONE)
        accounting.add(2, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(3, ActionToken.NONE, ActionToken.EXPLOIT)
        accounting.add(4, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.AUTH)
        accounting.add(5, ActionToken.AUTH, ActionToken.DATA)

        solver2 = Solver(tables2, accounting)
        res = solver2.solve_all(5,5,5, [ActionToken.DATA])
        for i, sol in enumerate(res):
            print(i, solver2.show(sol))


    if keyword == "cross-diamond":
        tables2 = Tables(CRD_hosts, CRD_services, CRD_actions, CRD_tokens)
        tables2.hhm = CRD_HH
        tables2.asm = CRD_AS
        tables2.atm = CRD_AT
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.START, ActionToken.START)
        accounting.add(1, ActionToken.NONE, ActionToken.EXPLOIT)
        accounting.add(2, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(3, ActionToken.EXPLOIT | ActionToken.SESSION, ActionToken.AUTH)
        accounting.add(4, ActionToken.SESSION , ActionToken.SESSION)
        accounting.add(5, ActionToken.AUTH | ActionToken.SESSION, ActionToken.DATA)
        accounting.add(6, ActionToken.DATA, ActionToken.END)

        solver2 = Solver(tables2, accounting)
        res = solver2.solve_all(6, 6, 6, [ActionToken.END])
        for i, sol in enumerate(res):
            print(i, solver2.show(sol))

    if keyword == "double-cross-diamond":
        tables2 = Tables(DCD_hosts, DCD_services, DCD_actions, DCD_tokens)
        tables2.hhm = DCD_HH
        tables2.asm = DCD_AS
        tables2.atm = DCD_AT
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.START, ActionToken.START)
        accounting.add(1, ActionToken.NONE, ActionToken.EXPLOIT)
        accounting.add(2, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(3, ActionToken.EXPLOIT | ActionToken.SESSION, ActionToken.AUTH)
        accounting.add(4, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.DATA)
        accounting.add(5, ActionToken.AUTH | ActionToken.DATA, ActionToken.NONE)
        accounting.add(6, ActionToken.DATA, ActionToken.END)

        solver2 = Solver(tables2, accounting)
        res = solver2.solve_all(5, 5, 5, [ActionToken.NONE])
        for i, sol in enumerate(res):
            print(i, solver2.show(sol))

    if keyword == "alternative-paths":
        tables2 = Tables(AP_hosts, AP_services, AP_actions, AP_tokens)
        tables2.hhm = AP_HH
        tables2.asm = AP_AS
        tables2.atm = AP_AT
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.START, ActionToken.START)
        accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(2, ActionToken.SESSION, ActionToken.SESSION)
        accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        accounting.add(2, ActionToken.SESSION, ActionToken.SESSION|ActionToken.EXPLOIT)
        accounting.add(3, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(4, ActionToken.NONE, ActionToken.EXPLOIT)
        accounting.add(5, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.AUTH)
        accounting.add(6, ActionToken.SESSION|ActionToken.EXPLOIT, ActionToken.DATA)
        accounting.add(6, ActionToken.AUTH, ActionToken.DATA)
        accounting.add(7, ActionToken.DATA, ActionToken.END)

        solver2 = Solver(tables2, accounting)
        res = solver2.solve_all(7, 7, 7, [ActionToken.END])
        for i, sol in enumerate(res):
            print(i, solver2.show(sol))

    if keyword == "alternative-paths2":
        tables2 = Tables(AP_hosts, AP_services, AP_actions, AP_tokens)
        tables2.hhm = AP2_HH
        tables2.asm = AP_AS
        tables2.atm = AP_AT
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.START, ActionToken.START)
        accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(2, ActionToken.SESSION, ActionToken.SESSION)
        accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        accounting.add(2, ActionToken.SESSION, ActionToken.SESSION|ActionToken.EXPLOIT)
        accounting.add(3, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(4, ActionToken.NONE, ActionToken.EXPLOIT)
        accounting.add(5, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.AUTH)
        accounting.add(6, ActionToken.SESSION|ActionToken.EXPLOIT, ActionToken.DATA)
        accounting.add(6, ActionToken.AUTH, ActionToken.DATA)
        accounting.add(7, ActionToken.DATA, ActionToken.END)

        solver2 = Solver(tables2, accounting)
        res = solver2.solve_all(7, 7, 7, [ActionToken.END])
        for i, sol in enumerate(res):
            print(i, solver2.show(sol))

    if keyword == "speartip":
        tables2 = Tables(ST_hosts, ST_services, ST_actions, ST_tokens)
        tables2.hhm = ST_HH
        tables2.asm = ST_AS
        tables2.atm = ST_AT
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.START, ActionToken.START)
        accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(2, ActionToken.SESSION, ActionToken.SESSION)
        accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        accounting.add(2, ActionToken.SESSION, ActionToken.SESSION | ActionToken.EXPLOIT)
        accounting.add(3, ActionToken.SESSION, ActionToken.SESSION)
        accounting.add(3, ActionToken.SESSION, ActionToken.EXPLOIT)
        accounting.add(3, ActionToken.SESSION, ActionToken.SESSION | ActionToken.EXPLOIT)
        accounting.add(4, ActionToken.SESSION, ActionToken.SESSION)
        accounting.add(4, ActionToken.SESSION, ActionToken.EXPLOIT)
        accounting.add(4, ActionToken.SESSION, ActionToken.SESSION | ActionToken.EXPLOIT)
        accounting.add(5, ActionToken.SESSION | ActionToken.EXPLOIT, ActionToken.AUTH)
        accounting.add(6, ActionToken.AUTH, ActionToken.DATA)

        solver2 = Solver(tables2, accounting)
        res = solver2.solve_all(6,6,6, [ActionToken.DATA])
        for i, sol in enumerate(res):
            print(i, solver2.show(sol))

        print(solver2.all_needed_tokens)


    if keyword == "cluster":

        tables = Tables(clus_hosts, clus_services, clus_actions, clus_tokens)
        tables.hhm = clus_HH
        tables.asm = clus_AS
        tables.atm = clus_AT
        tables.clusters = clus_CT
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.START, ActionToken.START)
        accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(2, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(3, ActionToken.SESSION, ActionToken.AUTH)
        accounting.add(4, ActionToken.SESSION , ActionToken.AUTH)
        accounting.add(5, ActionToken.AUTH, ActionToken.DATA)

        solver1 = Solver(tables, accounting)
        res = solver1.solve_all(5, 5, 5, [ActionToken.DATA])
        for i, sol in enumerate(res):
            print(i, solver1.show(sol))

        print(solver1.all_needed_tokens)

    if keyword == "trident":

        tables = Tables(trident_hosts, trident_services, trident_actions, trident_tokens)
        tables.hhm = trident_HH
        tables.asm = trident_AS
        tables.atm = trident_AT
        tables.dummies = trident_dummies
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.START, ActionToken.START)
        accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        accounting.add(3, ActionToken.SESSION, ActionToken.AUTH)
        accounting.add(4, ActionToken.SESSION, ActionToken.AUTH)

        solver1 = Solver(tables, accounting)
        res = solver1.solve_all(4, 4, 4, [ActionToken.AUTH])
        for i, sol in enumerate(res):
            print(i, solver1.show(sol))

    if keyword == "long-trident":

        tables = Tables(lt_hosts, lt_services, lt_actions, lt_tokens)
        tables.hhm = lt_HH
        tables.asm = lt_AS
        tables.atm = lt_AT
        tables.dummies = lt_dummies
        accounting = TokensAccounting()
        accounting.add(0, ActionToken.START, ActionToken.START)
        accounting.add(1, ActionToken.NONE, ActionToken.SESSION)
        accounting.add(2, ActionToken.SESSION, ActionToken.EXPLOIT)
        accounting.add(3, ActionToken.SESSION, ActionToken.AUTH)
        accounting.add(4, ActionToken.SESSION, ActionToken.AUTH)
        accounting.add(5, ActionToken.EXPLOIT, ActionToken.DATA)


        solver1 = Solver(tables, accounting)
        res = solver1.solve_all(6, 4, 4, [ActionToken.AUTH])
        for i, sol in enumerate(res):
            print(i, solver1.mappings(sol))




if __name__ == '__main__':
    main()
