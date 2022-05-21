from csv import DictReader
import quopri

class PredictiveModel():
    def __init__(self, datafile) -> None:
        self.predictions = {}
        keystr = ""
        for i in range(2):
            if i == 0:
                keystr = "s"
            else:
                keystr = "b"
            for j in range(-5, 11):
                keystr1 = keystr + f"s{j}"
                for k in range(11):
                    keystr2 = keystr1 + f"o{k}"
                    for t in range(4):
                        time = t*5
                        keystr3 = keystr2 + f"t{time}+"
                        for r in range(4):
                            rem = r*0.25
                            keystr4 = keystr3 + f"rem{rem}+"
                            self.predictions[keystr4] = [0,0,1,0]

    def generate_key(self, datapoint):
        keystr = ""
        if datapoint['level'] == 'buyer':
            keystr += "b"
        else:
            keystr += "s"
        keystr += f"s{datapoint['my_remaining_exog']}"
        keystr += f"o{datapoint['opp_last_exog']}"
        for t in range(4):
            if int(datapoint['time']) <= (t+1)*5:
                keystr += f"t{t*5}+"
                break
        for r in range(4):
            if float(datapoint['rem_negotiations']) <= (r+1)*0.25:
                keystr += f"rem{r*0.25}+"
                break
        return keystr

    def __call__(self, key):
        return self.predictions[key]

class MeanModel(PredictiveModel):
    def __init__(self, datafile) -> None:
        super().__init__(datafile)
        kecount = 0
        with open(datafile, 'r') as my_file:
            csv_reader = DictReader(my_file)
            for i in csv_reader:
                key = self.generate_key(i)
                try:
                    # quantity sum
                    self.predictions[key][0] += int(i['q'])
                    # adjusted price sum
                    self.predictions[key][1] += (float(i['p']) - float(i['min_price'])) / float(i['max_price']) * int(i['q'])
                    # count
                    self.predictions[key][2] += 1
                except KeyError:
                    kecount += 1
                    continue
        
        #print(f"kecount: {kecount}")
        for v in self.predictions.values():
            q = v[0]
            p = v[1]
            count = v[2]
            if q != 0:
                v[1] = p/q
            v[0] = q / count

        #print(self.predictions)

    def __call__(self, key, min_price, max_price):
        try:
            pred = self.predictions[key][:2].copy()
            pred[1] = (pred[1] * (max_price - min_price)) + min_price
            return pred
        except KeyError:
            return [0, 0]

class MeanOrDisagreementModel(PredictiveModel):
    def __init__(self, datafile) -> None:
        super().__init__(datafile)
        kecount = 0
        with open(datafile, 'r') as my_file:
            csv_reader = DictReader(my_file)
            for i in csv_reader:
                key = self.generate_key(i)
                try:
                    if int(i['q']) != 0:
                        # quantity sum
                        self.predictions[key][0] += int(i['q'])
                        # adjusted price sum
                        self.predictions[key][1] += (float(i['p']) - float(i['min_price'])) / float(i['max_price']) * int(i['q'])
                        # count
                        self.predictions[key][2] += 1
                    else:
                        # disagreement count
                        self.predictions[key][3] += 1
                except KeyError:
                    kecount += 1
                    continue
        print(kecount)

        for k, v in self.predictions.items():
            self.predictions[k] = self.normalize_prediction(v)

    def __call__(self, key, min_price, max_price):
        try:
            pred = self.predictions[key].copy()
            pred[1] = (pred[1] * (max_price - min_price)) + min_price
            return pred
        except KeyError:
            return [0, 0, 0, 1]

    def normalize_prediction(self, v):
        norm_v = [-1] * 4
        q = v[0]
        p = v[1]
        agree_count = v[2]
        disagree_count = v[3]
        total_negotiations = v[2] + v[3]
        if q != 0:
            norm_v[1] = p / q
        else:
            norm_v[1] = 0.5
        norm_v[0] = q / agree_count
        norm_v[2] = agree_count / total_negotiations
        norm_v[3] = disagree_count / total_negotiations
        return norm_v


class MeanByQuantityModel(PredictiveModel):
    def __init__(self, datafile) -> None:
        super().__init__(datafile)