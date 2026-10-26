# Это твоя игра. Меняй героя, реплики и правила!
# pet_window.py — готовое окно; его устройство изучать пока не нужно.
from pet_window import start, show, choose, say, finish

name = "Туманчик"
start(name, "Облачный лис")
say("Привет! Я", name, "— облачный лис. Я ем туман и ловлю ветер.")

hunger = 3
energy = 7
mood = 5
day = 1
total_days = 10

while day <= total_days:
    show(hunger, energy, mood, day, total_days)
    choice = choose("Покормить", "Ловить ветер", "Спать")

    if choice == "1":
        hunger = hunger - 3
        say(name, "съел миску тумана. Вкусно!")
    elif choice == "2":
        mood = mood + 2
        energy = energy - 2
        say(name, "поймал ветер за хвост!")
    elif choice == "3":
        energy = energy + 3
        say(name, "свернулся клубочком на облаке.")

    hunger = hunger + 1
    mood = mood - 1

    hunger = max(0, min(10, hunger))
    energy = max(0, min(10, energy))
    mood = max(0, min(10, mood))

    if hunger >= 8:
        say("Твой рюкзак выглядит подозрительно съедобным…")
    if energy <= 2:
        say("Даже ветер сегодня слишком быстрый. Я устал.")
    if mood >= 7:
        say("Мне так весело! Давай дружить всегда!")

    day = day + 1

# Последнее действие тоже должно изменить показатели на экране.
show(hunger, energy, mood, total_days, total_days)

if mood >= 7:
    title = "Твоё звание — Легенда весёлых приключений!"
elif energy >= 7:
    title = "Твоё звание — Хранитель облачных снов!"
else:
    title = "Твоё звание — Исследователь лисьих привычек!"

finish(title, "Наше приключение закончилось. До новой встречи!")
