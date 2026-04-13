import math
schedule=[[('MC Alger','USM Alger'),('MC Oran','CS Constantine')],[('USM Alger','MC Oran'),('CS Constantine','MC Alger')]]
def haversine(lat_away, lon_away, lat_home, lon_home):
    R = 6371 

    lat_away = math.radians(lat_away)
    lon_away = math.radians(lon_away)
    lat_home = math.radians(lat_home)
    lon_home = math.radians(lon_home)

    dlat = lat_home - lat_away
    dlon = lon_home - lon_away

    a = math.sin(dlat/2)**2 + math.cos(lat_away)*math.cos(lat_home)*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    distance = R * c
    return distance
Teams=['A','B','C','D']#the real teams will be provided according to the data of fadoua
import csv
teams=[]
with open("C:/Users/salmi/Downloads/teams.csv","r") as file:
    data=csv.DictReader(file)
    for row in data:
        teams.append(row)

    print("the teams are: ")
    print(teams)
dict_Matric={}
for home in teams:
    for away in teams:
        if home!=away:
           dict_Matric[(away["team"],home["team"])]=haversine(float(away["latitude"]),float(away["longitude"]),float(home["latitude"]),float(home["longitude"]))


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
