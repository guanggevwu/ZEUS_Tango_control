# Attributes

A few attributes worth a detailed description here. Also, hover the mouse over the attribute labels on the GUI, you sometimes can get a brief description.

## saved location source (saved_location_source)

Require restart client GUI to take effect in the GUI. If set to "server", use the "...server_locations.txt" on the server computer. If set to "client", use "...client_locations.txt" on the client computer. These text files are in the same folder as the Python script. Only works when the txt files are not empty. For example, if the attribute is set to "client" but the "...client_locations.txt" is empty, the server side saved locations will still be used.

## user defined locations (user_defined_locations)

The user defined location is the location list that read from the source assigned from "saved_location_source". It is a read and write attribute but it can't be edit from the GUI.

## current location (current_location)

The current location is determined by compare the current coordinates of the stages with the "user_defined_locations" list. For example, The current coordinates is (1.0, 2.0, 3.0) which means the location of the axis 1, 2, 3 are at 1mm, 2mm and 3mm, respectively. In the "user_defined_locations" list, there is a row called "some_location: (1,2)". In this case the current coordinates match the one in the list (though the axis 3 is not defined), the "current location" shows "some_location: (1,2)".
We can also select a location from the dropdown list as the destination and the stages will move to the selected destination.
If we use text command "[tango_device_proxy].current_location = [something]" to set the destination, [something] needs to be the text before ":", i.e. "some_location" but not "some_location: (1,2)" in the example above.

# Format of txt files for user defined locations

The two kinds of file, "...server_locations.txt" and "...client_locations.txt", have the same format.
Space is used a delimiters. No space should be contained in name or positions. The positions of multiple axes are separated by "," without a space.
