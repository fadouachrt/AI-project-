def findDerbiePenalties(derbies,team1,team2,schedule):
    penalty=0
    isDerbie=(team1,team2) in derbies or (team2,team1) in derbies
    if not isDerbie:
        return 0
# now we are sure that the match is a derbie m3ntha we try to calculate penalties ida l9ina
    for i,Round in enumerate(schedule):# n5dmo biha psq tmdli (index,value)
        for match in Round:
            home,away=match
            if ((team1==home and team2==away) or (team2==home and team1==away)):
                if(i % 2 !=0):
                    penalty+=1
                    print(f"derbies not in weekend 'round{i}'!!!!\n")        
    return penalty

def findRestDayPenalties(team1,schedule):
   rest_days=0
   last_played=None
   for i,round_ in enumerate(schedule):
       play=False
       for match in round_:
           home,away=match
           if(team1==home or team1==away):
               play=True
       if play:
           if last_played is not None:
               rest_days+=i-last_played-1
           last_played=i
    return rest_days

def findPenalties(team,schedule):
{
    penalty=0
    counter=0
    for round in schedule:
        for match in round:
            home,away=match
            if(team==away):
                counter+=1;
            elif(team==home):
                counter=0;
            if(counter>2):
                penalty+=1;

    return penalty
}
