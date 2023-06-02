# Aufgabe 1.1
class Dictionary:
    """
    Simple dictionary class to store tuples according to their hash keys.
    """

    def __init__(self, bucket_count=5):
        self.size = bucket_count
        self.buckets = [[] for _ in range(bucket_count)]

    def get_hash_of(self, t) -> int:
        return hash(t) % self.size

    def insert(self, k):
        hash_t: int = self.get_hash_of(k)
        found_key_value_pair = [key_value_pair for key_value_pair in self.buckets[hash_t] if k in key_value_pair[0]]
        if len(found_key_value_pair) >= 1:
            added_frequency_tuple = (found_key_value_pair[0][0], found_key_value_pair[0][1] + 1)
            self.buckets[hash_t].remove(found_key_value_pair[0])
            self.buckets[hash_t].append(added_frequency_tuple)
            return
        self.buckets[hash_t].append((k, 1))
        return

    def delete(self, k):
        hash_t: int = self.get_hash_of(k)
        found_key_value_pair = [key_value_pair for key_value_pair in self.buckets[hash_t] if k in key_value_pair[0]]
        if len(found_key_value_pair) > 0:
            self.buckets[hash_t].remove(found_key_value_pair[0])

    def get(self, k):
        hash_t: int = self.get_hash_of(k)
        found_key_value_pair = [key_value_pair for key_value_pair in self.buckets[hash_t] if k in key_value_pair[0]]
        return found_key_value_pair[0] if len(found_key_value_pair) > 0 else None

    def items(self):
        return_list = []
        for i in range(self.size):
            for each in self.buckets[i]:
                return_list.append(each)
        return return_list

# Aufgabe 1.2

text = ""
with open("/Users/bjakfar/studies/Dokumente/2/AuD/praktikum_2/Faust I.txt") as file:
    for line in file:
        text += line.rstrip()
faust_1_to_list = text.lower() \
    .replace("!", "") \
    .replace(":", "") \
    .replace(",", "") \
    .replace(".", "") \
    .replace("?", "") \
    .replace("(", "") \
    .replace(")", "") \
    .replace("-", "") \
    .replace(";", "") \
    .replace(";", "") \
    .split(" ")

processed = [x for x in faust_1_to_list if x]

faust_1 = Dictionary(1000)
for word in processed:
    faust_1.insert(word)

faust_1_sorted = faust_1.items()
faust_1_sorted.sort(key=lambda x: x[1])
# print(faust_1_sorted)
# print("Faust 1")

text2 = ""
with open("/Users/bjakfar/studies/Dokumente/2/AuD/praktikum_2/Faust II.txt") as file:
    for line in file:
        text2 += line.rstrip()
# print(text2)

faust_2_to_list = text2.lower() \
    .replace("!", "") \
    .replace(":", "") \
    .replace(",", "") \
    .replace(".", "") \
    .replace("?", "") \
    .replace("(", "") \
    .replace(")", "") \
    .replace("-", "") \
    .replace(";", "") \
    .replace(";", "") \
    .split(" ")

processed_faust_2 = [x for x in faust_2_to_list if x]

for word in processed_faust_2:
    faust_1.delete(word)

faust_1_filtered_sorted = faust_1.items()
faust_1_filtered_sorted.sort(key=lambda x: x[1])
# a[start:stop:step]
print(faust_1_filtered_sorted[:-10:-1])
print("")


# Aufgabe 2
# Set up dictionary with Faust I words
dict = {}
for word in processed:
    if word in dict:
        dict[word] += 1
        continue
    dict[word] = 1

for word in processed_faust_2:
    if word in dict:
        dict.pop(word)

print('10 most frequent words in Faust I, not appearing in Faust II:\n')
items = sorted(dict.items(), key=lambda x: x[1])
print(items[:-10:-1])
