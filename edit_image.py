from PIL.Image import Image


class EditImage(object):
    new_data = []

    def __init__(self, img, background_color=(255, 255, 255, 255), perimeter_points=None, probe_points=None):
        if not isinstance(img, Image):
            raise AttributeError("Must pass an Image object as first argument")
        self.image = img.convert("RGBA")
        self.background_color = background_color
        self.perimeter_points = []
        if perimeter_points:
            for perimeter in perimeter_points:
                self.add_perimeter(perimeter)
        self.probe_points = []
        if probe_points:
            self.add_probe_points(*probe_points)

    def add_probe_points(self, *points):
        for i, point in enumerate(points):
            if not isinstance(point, tuple):
                raise AttributeError("Point {} is not a tuple".format(point))
            if len(point) != 2:
                raise AttributeError("{} does not contain 2 items".format(point))
            item = self.image.getpixel(point)
            if item != self.background_color:
                raise AttributeError("Color of Point {} does not match background color".format(point))
        self.probe_points = points

    def add_perimeter(self, *points):
        if len(points) > 2:
            raise AttributeError("Perimeter must be 3 points or more")
        for i, point in enumerate(points):
            if not isinstance(point, tuple):
                raise AttributeError("Point {} is not a tuple".format(point))
            if len(point) != 2:
                raise AttributeError("Point must contain 2 items".format(point))
        self.perimeter_points.append(points)

    def get_direction_points(self, direction, target):
        width, height = self.image.size
        connected = None
        points = []
        point_index = 0 if direction in ["left", "right"] else 1
        direction_ranges = {
            "left": ((x1, target[1]) for x1 in reversed(range(0, target[0]))),
            "right": ((x1, target[1]) for x1 in range(target[0], width)),
            "up": ((target[0], y1) for y1 in reversed(range(0, target[1]))),
            "down": ((target[0], y1) for y1 in range(target[1], height))
        }
        for point in direction_ranges[direction]:
            item = self.image.getpixel(point)
            if item != self.background_color:
                if connected:
                    if abs(connected[-1][point_index] - point[point_index]) == 1:
                        connected.append(point)
                        continue
                    else:
                        points.append(connected[0])
                connected = [point]
        if connected:
            points.append(connected[0])
        return points

    def get_perimeters(self):
        found_perimeters = []
        for point in self.probe_points:
            starting_points = {}
            for direction in ["left", "right", "up", "down"]:
                points = self.get_direction_points(direction, point)
                starting_points[direction] = points
            min_points = (None, float('inf'))
            for k, v in starting_points.items():
                if len(v) < min_points[1]:
                    min_points = (k, len(v))
            enclosed = None
            try:
                for sp in starting_points[min_points[0]]:
                    enclosed, perimeter = self.build_perimeter(sp, point, starting_points)
                    if enclosed:
                        found_perimeters.append(perimeter)
                        break
                if not enclosed:
                    print("Could not find perimeter for pixel {}".format(point))
            except RecursionError:
                print("RecursionError: pixel {}".format(point))
        return found_perimeters

    @staticmethod
    def point_distance(p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def count_surrounding_background_pixels(self, point):
        s_points = [(point[0] + x1, point[1] + y1)
                    for x1, y1 in ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))]

        def sum_background_pixels(s_point):
            item = self.image.getpixel(s_point)
            return 1 if item == self.background_color else 0

        return sum(map(sum_background_pixels, s_points))

    @staticmethod
    def connect_points(points):
        perimeter = []
        for i in range(0, len(points)):
            from_point = points[i]
            to_point = points[0 if len(points) == i + 1 else i + 1]
            dist = [from_point[index] - to_point[index] for index in range(2)]
            max_dist = max(*dist)
            for multiplier in range(1, max_dist + 1):
                perimeter.append(tuple([round(from_point[index] + (dist[index] / max_dist) * multiplier)
                                        for index in range(2)]))
        return perimeter

    def build_perimeter(self, current_point, target, probe_points,
                        points_probed=(), directions=(), starting_point=None):
        if not starting_point:
            starting_point = current_point
        if current_point[0] == target[0]:
            diff = current_point[1] - target[1]
            next_direction = "left" if diff > 0 else "right"
            if next_direction not in directions:
                directions = tuple(list(directions) + [next_direction])
        if current_point[1] == target[1]:
            diff = current_point[0] - target[0]
            next_direction = "down" if diff > 0 else "up"
            if next_direction not in directions:
                directions = tuple(list(directions) + [next_direction])
        surrounding_points = [(current_point[0] + x1, current_point[1] + y1)
                              for x1, y1 in ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))]
        current_direction = directions[-1]
        to_point = probe_points[current_direction][0]
        from_point = probe_points[directions[-2]][0] if len(directions) > 1 else starting_point

        def sort_points(p2):
            to_distance = self.point_distance(to_point, p2)
            index = 0 if current_direction in ["left", "right"] else 1
            dir_factor = -1 if current_direction in ["left", "up"] else 1
            from_distance = dir_factor * (from_point[index] - p2[index])
            pixels = min(self.count_surrounding_background_pixels(p2), 2)
            return to_distance + from_distance - pixels

        surrounding_points = sorted(surrounding_points, key=sort_points)
        for point in surrounding_points:
            if point[0] >= 1 and point[1] >= 0:
                pixel = self.image.getpixel(point)
                if not (pixel[0] == 255 and pixel[1] == 255 and pixel[2] == 255):
                    if point == starting_point and len(directions) == 4:
                        return True, tuple(list(points_probed) + [current_point])
                    if point not in points_probed:
                        surrounded, points_probed = self.build_perimeter(point, target, probe_points,
                                                                         points_probed=tuple(
                                                                             list(points_probed) + [current_point]),
                                                                         directions=directions,
                                                                         starting_point=starting_point)
                        if surrounded:
                            return surrounded, points_probed
        return False, points_probed

    @staticmethod
    def in_perimeter(point, color_points, perimeter):
        x, y = point
        in_perimeter = True
        for gt, index in [(False, 0), (True, 0), (False, 1), (True, 1)]:
            if not in_perimeter:
                break
            in_perimeter = False
            axis = list(filter((lambda val: bool(val > point[index]) == gt),
                               color_points.keys() if index == 1 else color_points.get(y, [])))
            for val2 in axis:
                p = [None, None]
                p[index] = val2
                p[abs(index - 1)] = point[abs(index - 1)]
                if tuple(p) in perimeter:
                    in_perimeter = True
                    continue

        return in_perimeter

    def split_image_colors(self):
        width, height = self.image.size
        background_points = {}
        color_points = {}
        for y in range(0, height):
            row = []
            color_row = []
            left = False
            for x in range(0, width):
                item = self.image.getpixel((x, y))
                if item == self.background_color:
                    up = False
                    for y1 in range(0, y):
                        cp = color_points.get(y1, {})
                        up = x in cp
                    if left and up:
                        row.append(x)
                else:
                    color_row.append(x)
                    left = True
            background_points[y] = row
            color_points[y] = color_row
        return background_points, color_points

    def get_new_data(self, found_perimeters, new_background):
        background_points, color_points = self.split_image_colors()
        width, height = self.image.size
        data = []
        for y in range(0, height):
            for x in range(0, width):
                point = (x, y)
                item = self.image.getpixel(point)
                if item == self.background_color:
                    background = True
                    if y in background_points and x in background_points[y]:
                        for perimeter in found_perimeters:
                            if self.in_perimeter(point, color_points, perimeter):
                                background = False
                                break
                    if background:
                        data.append(new_background)
                    else:
                        data.append(item)
                else:
                    data.append(item)
        return data

    def change_background(self, background_color=(255, 255, 255, 0)):
        found_perimeters = self.get_perimeters()
        new_data = self.get_new_data(found_perimeters, background_color)
        self.new_data = new_data
        self.image.putdata(new_data)

    def save(self, path, file_format="PNG"):
        self.image.save(path, file_format)
