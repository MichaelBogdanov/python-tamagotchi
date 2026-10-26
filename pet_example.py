print("10 дней с необычным питомцем")
print("Я — облачный лис. Я ем туман и люблю ловить ветер.")
name = input("Как назовём питомца? ")
print("Приятно познакомиться! Меня зовут", name)

hunger = 3
energy = 7
mood = 5
day = 1
total_days = 10

while day <= total_days:
    print()
    print("День", day, "из", total_days)
    print("Голод:", hunger, "/ 10 — меньше значит лучше")
    print("Энергия:", energy, "/ 10 — больше значит лучше")
    print("Настроение:", mood, "/ 10 — больше значит лучше")

    print("1 — Покормить туманом")
    print("2 — Поиграть в ловлю ветра")
    print("3 — Уложить спать на облаке")
    choice = input("Введи 1, 2 или 3 и нажми Enter: ")

    while choice != "1" and choice != "2" and choice != "3":
        print("Такой команды пока нет. Попробуй ещё раз.")
        choice = input("Введи 1, 2 или 3: ")

    if choice == "1":
        hunger = hunger - 3
        print(name, "съел миску тумана. Вкусно!")
    elif choice == "2":
        mood = mood + 2
        energy = energy - 2
        print(name, "поймал ветер за хвост!")
    elif choice == "3":
        energy = energy + 3
        print(name, "свернулся клубочком на облаке.")

    hunger = hunger + 1
    mood = mood - 1

    hunger = max(0, min(10, hunger))
    energy = max(0, min(10, energy))
    mood = max(0, min(10, mood))

    print("К вечеру: голод —", hunger, "энергия —", energy, "настроение —", mood)

    if hunger >= 8:
        print(name, "смотрит на твой рюкзак: а он съедобный?")
    if energy <= 2:
        print(name, "зевает: даже ветер сегодня слишком быстрый.")
    if mood >= 7:
        print(name, "рисует в небе сердечко!")

    day = day + 1

print()
print("Наши", total_days, "дней закончились!")
print("Итоговый голод:", hunger)
print("Итоговая энергия:", energy)
print("Итоговое настроение:", mood)

if mood >= 7:
    print("Твоё звание — Легенда весёлых приключений!")
elif energy >= 7:
    print("Твоё звание — Хранитель облачных снов!")
else:
    print("Твоё звание — Исследователь лисьих привычек!")

print("До новой встречи! — говорит", name)
