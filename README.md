# py4web simple table

A collection of different ways to display a grid in py4web.

* Simple Table - My shot at a reusable table
* HTML Grid - the HTML grid from py4web
* Datatables.net - sample implementation of a reusable datatables.net table
* py4web AJAX grid - AJAX grid using mtable
* py4web Vue.js grid - a Vue.js grid in py4web

All three examples are working over the same sqlite database of zip code I downloaded freely from the web which contains just over 42,000 records.

##### This is a work in progress

Random thoughts on each

#### Simple Table
A CRUD tool for py4web.  Similar to what SQLFORM.grid provided in web2py.  Not close to being as flexible.  Needs to be vetted for security vulnerabilities.

Search is different that web2py SQLFORM.grid.  In essense, you provide your own FORM that will be rendered and then you build the queries to pass to SimpleTable for it to get the data.

#### HTML Grid
* I like my edit buttons the right side of each row - I need to work on adding that
* Paging seems to be off a little bit - I will submit a PR
* filtering - if you return no rows, you lose all your column header except for the ones where there is a filter
* the paging buttons move around too much - I like to be able to page without moving my mouse.  The next button moves around based on the text before it (obviously).  Would like a different paging control.
* formatting - I seem to recall Massimo saying we needed to add some standardized css classes so people can modify the look and feel.

#### datatables.net
* Formatting was a concern but now I'm happy with how it is working
* Edit and Delete controls are working - need a confirmation popup before delete

#### AJAX Grid
* I don't care for the layout
* No paging controls, only allows you to retrieve more rows which are then added on to the end of the rows you'd already retrieved
* Confusing search control - I can't figure out how to search by Primary City in my app
* I don't think I'll be looking at this any more as I just don't like the way it worked.

#### Vue.js Grid
* Not sure how this is supposed to work.  I couldn't get a sample working wiht my table

 
