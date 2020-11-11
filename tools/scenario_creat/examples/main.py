from tools.scenario_creat.examples.scenarios import Path, Diamond, CrossDiamond, DoubleCrossDiamond,\
    AlternativePaths, AlternativePaths2, Speartip, Trident, LongTrident, BronzeButler, BrBuCto, BrBuVPN

def main():
    scenario = BronzeButler()
    #scenario.show_graph()
    scenario.solve_all()



if __name__ == '__main__':
    main()