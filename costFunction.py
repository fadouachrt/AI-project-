def costFunction(schedule,dict_Matric,derbies,teams):
    rest=[]
    penalty=0
    totaDistance=total_distance(schedule,dict_Matric)
    for team in teams:
        penalty+=findPenalties(team,schedule)   
        rest.append(findRestDayPenalties(team,schedule))
    penalty+=max(rest)-min(rest)
    for round_ in schedule:
        for match in round_:
            home,away=match
            penalty+=findDerbiePenalties(derbies,home,away,schedule)
    cost=totalDistance+1000*penalty
    return cost
