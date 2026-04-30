def total_distance(schedule,dict_Matric):
    total=0
    for round in schedule:
       for match in round:
           home,away=match
           total+=dict_Matric[(away,home)]
           print(f"the team {away} will travel to {home} wiht distance: {dict_Matric[(away,home)]} km"
                )
    return total
total=total_distance(schedule,dict_Matric)
print(f"the total distance is: {total} km")
