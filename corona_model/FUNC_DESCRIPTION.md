This file lists the functionality and how to modify the code with ease.





1.) starting the model:

x = Agent_based_model()
x.load_data()
x.initilaize()
x.initilize_agents()
x.initilize_storing_parameters()

for _ in range(10):
    model.update_time()
    model.store_information()
    model.print_relevant_info()


2.) 



---

## Schedule creation

O = odd days, E = even days, W = weekends

what an empty schedule looks like (3 rows for O, E, and W):

[[0, 0, 0, 0, 0 ,0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0, 0 ,0]<br/>
[0, 0, 0, 0, 0 ,0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0, 0 ,0]<br/>
[0, 0, 0, 0, 0 ,0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0, 0 ,0, 0, 0, 0, 0, 0 ,0]]


The classroom availability and capacity:

| Classroom | Capacity | available days |
|-----------|----------|----------------|
| A | 5 | O, E |
| B | 5| O, E |
| C | 5|O, E |
| D | 5 |O |

From the information above, we make a new list
the new list will contain repeating room names (repeat for capacity #)

Odd days: [A, A, A, A, A, B, B, B, B, B, C, C, C, C, C, D, D, D, D, D]<br/>
Even days: [A, A, A, A, A, B, B, B, B, B, C, C, C, C, C]

Then each agent will have a boolean mask that looks like the one below<br/>
*the number of T and F is configurable *<br/>
    [   [T, F, T, F],<br/>
        [F, F, T, T]]
