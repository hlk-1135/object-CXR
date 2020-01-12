import argparse
from collections import namedtuple
import numpy as np
from skimage.measure import points_in_poly


Object = namedtuple('Object',
                    ['image_name', 'object_id', 'object_type', 'coordinates'])
Prediction = namedtuple('Prediction',
                        ['image_name', 'probability', 'coordinates'])


parser = argparse.ArgumentParser(description='Compute FROC')
parser.add_argument('gt_csv', default=None, metavar='GT_CSV',
                    type=str, help="Path to the ground truch csv file")
parser.add_argument('pred_csv', default=None, metavar='PRED_PATH',
                    type=str, help="Path to the predicted csv file")
parser.add_argument('--fps', default='1,2,4,8,16,32', type=str,
                    help='False positives per image to compute FROC, comma '
                    'seperated, default "1,2,4,8,16,32"')


def inside_object(pred, obj):
    # bounding box
    if obj.object_type == '0':
        x1, y1, x2, y2 = obj.coordinates
        x, y = pred.coordinates
        return x1 <= x <= x2 and y1 <= y <= y2
    # bounding ellipse
    if obj.object_type == '1':
        x_center, y_center = (x1 + x2) / 2, (y1 + y2) / 2
        x_axis, y_axis = (x2 - x1) / 2, (y2 - y1) / 2
        return ((x - x_center)/x_axis)**2 + ((y - y_center)/y_axis)**2 <= 1
    # mask/polygon
    if obj.object_type == '2':
        num_points = len(obj.coordinates) // 2
        poly_points = obj.coordinates.reshape(num_points, 2, order='C')
        return points_in_poly(pred.coordinates.reshape(1, 2), poly_points)[0]


def main():
    args = parser.parse_args()

    # parse ground truth csv
    num_image = 0
    num_object = 0
    object_dict = {}
    with open(args.gt_csv) as f:
        # header
        f.next()
        for line in f:
            image_name, annotation = line.strip('\n').split(',')

            if annotation == '':
                num_image += 1
                continue

            object_annos = annotation.split(';')
            for object_anno in object_annos:
                fields = object_anno.split(' ')
                object_type = fields[0]
                coords = np.list(map(float, fields[1:]))
                obj = Object(image_name, num_object, object_type, coords)
                if image_name in object_dict:
                    object_dict[image_name].append(obj)
                else:
                    object_dict[image_name] = [obj]
                num_object += 1
            num_image += 1

    # parse prediction truth csv
    preds = []
    with open(args.pred_csv) as f:
        # header
        f.next()
        for line in f:
            image_name, prediction = line.strip('\n').split(',')

            if prediction == '':
                continue

            coord_predictions = prediction.split(';')
            for coord_prediction in coord_predictions:
                fields = object_anno.split(' ')
                probability, x, y = list(map(float, fields))
                pred = Prediction(image_name, probability, np.array([x, y]))
                preds.append(pred)

    # sort prediction by probabiliyt
    preds = sorted(preds, key=lambda x: x.probability, reverse=True)

    # compute hits and false positives
    hits = 0
    false_positives = 0
    object_hitted = set()
    fps = list(map(int, args.fps.split(',')))
    froc = []
    finished = False
    for i in range(len(preds)):
        for obj in object_dict[image_name]:
            if inside_object(pred, obj):
                if obj.object_id in object_hitted:
                    pass
                else:
                    hits += 1
            else:
                false_positives += 1

            if false_positives / num_image >= fps[0]:
                sensitivity = hits / num_object
                froc.append(sensitivity)
                fps.pop(0)

                if len(fps) == 0:
                    finished = True
                    break

        if finished:
            break

    # print froc
    print('False positives per image:')
    print('\t'.join(args.fps.split(',')))
    print('Sensitivity:')
    print('\t'.join(map(lambda x: '{:.3f}'.format(x), froc)))
    print('FROC:')
    print(np.mean(froc))


if __name__ == '__main__':
    main()
