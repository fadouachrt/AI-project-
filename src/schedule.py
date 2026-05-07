#schedule.py
import random 
from models import Match , Round , Schedule 

def double_round_robin ( teams ) : 
    n = len( teams )
    if n % 2 != 0:
        raise ValueError(f"Need an even number of teams, got {n}")
    if n < 2:
        raise ValueError(f"Need at least 2 teams, got {n}")

    fixed = teams [ 0 ]
    rotating = list ( teams[1:] )
    
    first_leg = []
    for round_num in range ( n - 1 ):
        round_obj = Round ( round_index = round_num )
        if round_num % 2 == 0 : 
            round_obj.matches.append ( Match ( home = fixed , away = rotating [ 0 ]))
        else:
            round_obj.matches.append ( Match ( home = rotating [ 0 ] , away = fixed ))
        
        for i in range ( 1 , n // 2 ):
            team_a = rotating [ i ]
            team_b = rotating [ n - 1 - i ]
            if i % 2 == 0 :
                round_obj.matches.append ( Match ( home = team_a , away = team_b ))
            else : 
                round_obj.matches.append ( Match ( home = team_b , away = team_a ))
                
        first_leg.append(round_obj)
        
        last = rotating.pop()
        rotating.insert ( 0 , last )
        
    sec_leg = []
    for i , round_obj in enumerate(first_leg):
        mirror = Round ( round_index= (n-1) + i)
        for match in round_obj.matches : 
            mirror.matches.append( Match ( home = match.away , away = match.home ))
        
        sec_leg.append ( mirror )
        
    all_rounds = first_leg + sec_leg
    
    return Schedule ( rounds = all_rounds , teams= list ( teams ))

def assign_all_days ( schedule ) : 
    for round_obj in schedule.rounds : 
        assign_match_day ( round_obj )
        
    return schedule

def assign_match_day ( round_obj ) : 
    matches = round_obj.matches
    n = len ( matches )
    saturday_matches = matches [:1]
    friday_matches = matches[n-2:]
    third_matches = matches[1:n-2]
    
    for match in saturday_matches : 
        match.day = "Saturday"
    for match in friday_matches : 
        match.day = "Friday"
    for match in third_matches : 
        match.day = round_obj.third_day 
        
        
        