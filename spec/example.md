# Write Language Examples

Concrete, parser-friendly samples covering functions, arguments, typed decls, loops,
I/O, indexing, and phrase-style arithmetic.

## Basic function with defaults and named args

````write
function "sum_up" arguments:(a:int=0, b:int=0)
    return add a and b
end function

call "sum_up" with arguments:(a=3, b=4)
call "sum_up" with arguments:(5, 6)
````

## Lists/arrays, loops, conditions, and input

````write
make nums as list of size 5
set nums[0] to 1
set nums[1] to 2
set nums[2] to 3
set nums[3] to 4
set nums[4] to 5

input "Enter a multiplier: " factor as int

set i to 0
while i < 5 do
    set nums[i] to multiply nums[i] and factor
    add 1 to i
end while

for idx from 0 to 4 do
    if nums[idx] is greater than 10 then
        print "big:", nums[idx]
    else
        print "small:", nums[idx]
    end if
end for
````

## Combined control flow and returns

````write
func "clamp" arguments:(value, lo:int=0, hi:int=100)
    if value < lo then
        return lo
    else if value > hi then
        return hi
    else
        return value
    end if
end func
````
